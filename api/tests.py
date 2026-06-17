import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import Comment, Follow, GitHubAccount, Post, Profile, Repo

User = get_user_model()


def sample_repo_payload(full_name="django/django"):
    owner, name = full_name.split("/")
    return {
        "full_name": full_name,
        "name": name,
        "owner": {"login": owner, "avatar_url": "https://avatars.example/u.png"},
        "html_url": f"https://github.com/{full_name}",
        "description": "The Web framework for perfectionists with deadlines.",
        "homepage": "https://www.djangoproject.com/",
        "language": "Python",
        "topics": ["python", "web"],
        "stargazers_count": 79000,
        "forks_count": 31000,
        "open_issues_count": 120,
        "pushed_at": "2026-05-30T00:00:00Z",
    }


def make_user(username, password="testpass123!"):
    user = User.objects.create_user(username=username, password=password)
    Profile.objects.create(user=user)
    return user


def tiny_image(name="t.png"):
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return SimpleUploadedFile(name, io.BytesIO(data).read(), content_type="image/png")


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def alice(db):
    return make_user("alice")


@pytest.fixture
def bob(db):
    return make_user("bob")


@pytest.fixture
def auth_alice(api, alice):
    api.force_authenticate(user=alice)
    return api


@pytest.fixture
def mock_github(monkeypatch):
    from core import github

    def fake_fetch(full_name):
        return sample_repo_payload(full_name)

    monkeypatch.setattr(github, "fetch_repo_metadata", fake_fetch)
    return fake_fetch


class TestAuth:
    def test_register_creates_user_and_profile(self, api, db):
        resp = api.post(
            "/api/v1/auth/register/",
            {
                "username": "carol",
                "email": "carol@example.com",
                "password": "Sup3rSecret!",
                "password2": "Sup3rSecret!",
            },
            format="json",
        )
        assert resp.status_code == 201
        user = User.objects.get(username="carol")
        assert Profile.objects.filter(user=user).exists()

    def test_register_password_mismatch(self, api, db):
        resp = api.post(
            "/api/v1/auth/register/",
            {
                "username": "carol",
                "password": "Sup3rSecret!",
                "password2": "different",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_token_obtain(self, api, alice):
        resp = api.post(
            "/api/v1/auth/token/",
            {"username": "alice", "password": "testpass123!"},
            format="json",
        )
        assert resp.status_code == 200
        assert "access" in resp.data and "refresh" in resp.data

    def test_me_requires_auth(self, api, db):
        assert api.get("/api/v1/auth/me/").status_code == 401

    def test_me_returns_profile(self, auth_alice):
        resp = auth_alice.get("/api/v1/auth/me/")
        assert resp.status_code == 200
        assert resp.data["username"] == "alice"

    def test_me_creates_profile_for_profileless_user(self, api, db):
        # A user without a Profile (e.g. via createsuperuser) must not 500.
        user = User.objects.create_user(username="rootish", password="testpass123!")
        api.force_authenticate(user=user)
        resp = api.get("/api/v1/auth/me/")
        assert resp.status_code == 200
        assert resp.data["username"] == "rootish"
        assert Profile.objects.filter(user=user).exists()

    def test_register_rejects_reserved_username(self, api, db):
        resp = api.post(
            "/api/v1/auth/register/",
            {
                "username": "settings",
                "email": "s@example.com",
                "password": "Sup3rSecret!",
                "password2": "Sup3rSecret!",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "username" in resp.data


class TestPosts:
    def test_create_post_sets_author(self, auth_alice, alice):
        resp = auth_alice.post(
            "/api/v1/posts/",
            {"caption": "hello", "image": tiny_image()},
            format="multipart",
        )
        assert resp.status_code == 201
        assert resp.data["author"]["username"] == "alice"
        assert Post.objects.filter(user=alice).count() == 1

    def test_anonymous_cannot_create_post(self, api, db):
        resp = api.post("/api/v1/posts/", {"caption": "x"}, format="multipart")
        assert resp.status_code == 401

    def test_cannot_edit_others_post(self, api, alice, bob):
        post = Post.objects.create(user=bob, image=tiny_image(), caption="bob")
        api.force_authenticate(user=alice)
        resp = api.patch(f"/api/v1/posts/{post.id}/", {"caption": "hacked"}, format="json")
        assert resp.status_code == 403

    def test_like_toggle(self, auth_alice, bob):
        post = Post.objects.create(user=bob, image=tiny_image(), caption="bob")
        resp = auth_alice.post(f"/api/v1/posts/{post.id}/like/")
        assert resp.data == {"liked": True, "num_likes": 1}
        resp = auth_alice.post(f"/api/v1/posts/{post.id}/like/")
        assert resp.data == {"liked": False, "num_likes": 0}

    def test_filter_posts_by_author(self, auth_alice, bob):
        Post.objects.create(user=bob, image=tiny_image(), caption="by-bob")
        carol = make_user("carol")
        Post.objects.create(user=carol, image=tiny_image(), caption="by-carol")
        resp = auth_alice.get("/api/v1/posts/?author=bob")
        captions = {p["caption"] for p in resp.data["results"]}
        assert captions == {"by-bob"}

    def test_feed_only_followed_and_self(self, api, alice, bob):
        carol = make_user("carol")
        Post.objects.create(user=bob, image=tiny_image(), caption="from-bob")
        Post.objects.create(user=carol, image=tiny_image(), caption="from-carol")
        own = Post.objects.create(user=alice, image=tiny_image(), caption="mine")
        Follow.objects.create(follower=alice, following=bob)

        api.force_authenticate(user=alice)
        resp = api.get("/api/v1/posts/feed/")
        captions = {p["caption"] for p in resp.data["results"]}
        assert "from-bob" in captions
        assert "mine" in captions
        assert "from-carol" not in captions
        assert str(own.id)

    def test_feed_falls_back_to_discovery_when_following_nobody(self, api, alice, bob):
        # A user who follows nobody sees a global discovery feed, not a blank page.
        carol = make_user("carol")
        Post.objects.create(user=bob, image=tiny_image(), caption="from-bob")
        Post.objects.create(user=carol, image=tiny_image(), caption="from-carol")

        api.force_authenticate(user=alice)  # alice follows no one
        resp = api.get("/api/v1/posts/feed/")
        captions = {p["caption"] for p in resp.data["results"]}
        assert {"from-bob", "from-carol"} <= captions


class TestProfilesAndComments:
    def test_follow_toggle_and_counts(self, auth_alice, bob):
        resp = auth_alice.post("/api/v1/profiles/bob/follow/")
        assert resp.data == {"following": True}
        assert Follow.objects.filter(following=bob).count() == 1

        detail = auth_alice.get("/api/v1/profiles/bob/")
        assert detail.data["followers_count"] == 1
        assert detail.data["is_following"] is True

        resp = auth_alice.post("/api/v1/profiles/bob/follow/")
        assert resp.data == {"following": False}

    def test_cannot_follow_self(self, auth_alice):
        resp = auth_alice.post("/api/v1/profiles/alice/follow/")
        assert resp.status_code == 400

    def test_create_and_list_comments(self, auth_alice, bob):
        post = Post.objects.create(user=bob, image=tiny_image(), caption="bob")
        resp = auth_alice.post(
            "/api/v1/comments/",
            {"post": str(post.id), "body": "nice work"},
            format="json",
        )
        assert resp.status_code == 201
        assert Comment.objects.filter(post=post).count() == 1

        listing = auth_alice.get(f"/api/v1/comments/?post={post.id}")
        assert listing.data["count"] == 1

    def test_search_profiles(self, auth_alice):
        make_user("zebra")
        resp = auth_alice.get("/api/v1/profiles/?search=zeb")
        usernames = {p["username"] for p in resp.data["results"]}
        assert "zebra" in usernames


class TestGitHub:
    def test_parse_identifier_variants(self):
        from core.github import parse_repo_identifier

        assert parse_repo_identifier("django/django") == "django/django"
        assert parse_repo_identifier("https://github.com/django/django") == "django/django"
        assert parse_repo_identifier("https://github.com/django/django.git") == "django/django"
        assert parse_repo_identifier("https://github.com/django/django/issues/1") == "django/django"

    def test_parse_identifier_rejects_garbage(self):
        from core.github import parse_repo_identifier

        with pytest.raises(ValueError):
            parse_repo_identifier("not a repo")
        with pytest.raises(ValueError):
            parse_repo_identifier("https://gitlab.com/foo/bar")

    def test_resolve_repo(self, auth_alice, mock_github):
        resp = auth_alice.post(
            "/api/v1/github/resolve/",
            {"q": "https://github.com/django/django"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["full_name"] == "django/django"
        assert resp.data["language"] == "Python"
        assert "python" in resp.data["topics"]

    def test_resolve_invalid(self, auth_alice, mock_github):
        resp = auth_alice.post("/api/v1/github/resolve/", {"q": "nonsense"}, format="json")
        assert resp.status_code == 400

    def test_repo_detail_endpoint(self, auth_alice, mock_github):
        resp = auth_alice.get("/api/v1/github/repos/django/django/")
        assert resp.status_code == 200
        assert resp.data["full_name"] == "django/django"

    def test_attach_repo_to_post(self, auth_alice, alice, mock_github):
        resp = auth_alice.post(
            "/api/v1/posts/",
            {
                "caption": "shipping",
                "image": tiny_image(),
                "repo_full_name": "django/django",
            },
            format="multipart",
        )
        assert resp.status_code == 201
        assert resp.data["repo"]["full_name"] == "django/django"
        assert Repo.objects.filter(full_name="django/django").exists()
        assert Post.objects.get(user=alice).repo.full_name == "django/django"

    def test_filter_posts_by_repo(self, auth_alice, alice, bob, mock_github):
        from core.github import get_or_refresh_repo

        repo = get_or_refresh_repo("django/django")
        Post.objects.create(user=bob, image=tiny_image(), caption="tagged", repo=repo)
        Post.objects.create(user=alice, image=tiny_image(), caption="untagged")
        resp = auth_alice.get("/api/v1/posts/?repo=django/django")
        captions = {p["caption"] for p in resp.data["results"]}
        assert captions == {"tagged"}

    def test_repo_list_and_filters(self, auth_alice, mock_github):
        from core.github import get_or_refresh_repo

        get_or_refresh_repo("django/django")
        get_or_refresh_repo("pallets/flask")

        listing = auth_alice.get("/api/v1/github/repos/")
        names = {r["full_name"] for r in listing.data["results"]}
        assert {"django/django", "pallets/flask"} <= names

        owned = auth_alice.get("/api/v1/github/repos/?owner=pallets")
        assert {r["full_name"] for r in owned.data["results"]} == {"pallets/flask"}

        searched = auth_alice.get("/api/v1/github/repos/?search=flask")
        assert {r["full_name"] for r in searched.data["results"]} == {"pallets/flask"}

    def test_repo_list_mine(self, api, db, mock_github):
        from core.github import get_or_refresh_repo

        get_or_refresh_repo("django/django")  # owner "django"
        owner = make_user("django")
        GitHubAccount.objects.create(user=owner, github_id=555, login="django", access_token="t")
        api.force_authenticate(user=owner)
        resp = api.get("/api/v1/github/repos/?mine=1")
        assert {r["full_name"] for r in resp.data["results"]} == {"django/django"}

    def test_repo_list_mine_without_account_is_empty(self, auth_alice, mock_github):
        from core.github import get_or_refresh_repo

        get_or_refresh_repo("django/django")
        resp = auth_alice.get("/api/v1/github/repos/?mine=1")
        assert resp.data["results"] == []

    def test_profile_exposes_github_login(self, auth_alice, alice):
        GitHubAccount.objects.create(user=alice, github_id=777, login="alice-gh", access_token="t")
        resp = auth_alice.get("/api/v1/profiles/alice/")
        assert resp.data["github_login"] == "alice-gh"
        # Users without a linked account report null.
        make_user("nogh")
        resp2 = auth_alice.get("/api/v1/profiles/nogh/")
        assert resp2.data["github_login"] is None


@pytest.fixture
def oauth_settings(settings):
    settings.GITHUB_OAUTH_CLIENT_ID = "test-client-id"
    settings.GITHUB_OAUTH_CLIENT_SECRET = "test-secret"
    settings.GITHUB_OAUTH_SCOPES = "read:user,public_repo"
    settings.FRONTEND_URL = "http://localhost:3000"
    return settings


def make_state(user):
    from django.core import signing

    from api.views import GITHUB_OAUTH_SALT

    return signing.dumps({"uid": user.id}, salt=GITHUB_OAUTH_SALT)


class TestGitHubOAuth:
    def test_authorize_url_requires_auth(self, api, db, oauth_settings):
        resp = api.get("/api/v1/github/oauth/authorize-url/")
        assert resp.status_code == 401

    def test_authorize_url(self, auth_alice, oauth_settings):
        resp = auth_alice.get("/api/v1/github/oauth/authorize-url/")
        assert resp.status_code == 200
        url = resp.data["authorize_url"]
        assert "github.com/login/oauth/authorize" in url
        assert "client_id=test-client-id" in url
        assert "state=" in url

    def test_authorize_url_unconfigured(self, auth_alice, settings):
        settings.GITHUB_OAUTH_CLIENT_ID = ""
        resp = auth_alice.get("/api/v1/github/oauth/authorize-url/")
        assert resp.status_code == 503

    def test_callback_links_account(self, auth_alice, alice, oauth_settings, monkeypatch):
        from core import github

        monkeypatch.setattr(
            github,
            "exchange_oauth_code",
            lambda code, redirect_uri: {"access_token": "gho_x", "scope": "read:user"},
        )
        monkeypatch.setattr(
            github,
            "fetch_authenticated_user",
            lambda token: {"id": 4242, "login": "alice-gh", "avatar_url": "https://a/x.png"},
        )
        resp = auth_alice.post(
            "/api/v1/github/oauth/callback/",
            {"code": "abc", "state": make_state(alice)},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["login"] == "alice-gh"
        account = GitHubAccount.objects.get(user=alice)
        assert account.github_id == 4242
        assert account.access_token == "gho_x"

    def test_callback_rejects_bad_state(self, auth_alice, oauth_settings):
        resp = auth_alice.post(
            "/api/v1/github/oauth/callback/",
            {"code": "abc", "state": "tampered"},
            format="json",
        )
        assert resp.status_code == 400

    def test_callback_rejects_other_users_state(self, auth_alice, bob, oauth_settings):
        resp = auth_alice.post(
            "/api/v1/github/oauth/callback/",
            {"code": "abc", "state": make_state(bob)},
            format="json",
        )
        assert resp.status_code == 400


LOGIN_NONCE = "test-nonce-123"


def make_login_state(nonce=LOGIN_NONCE):
    from django.core import signing

    from api.views import GITHUB_LOGIN_SALT

    return signing.dumps({"flow": "login", "nonce": nonce}, salt=GITHUB_LOGIN_SALT)


def login_payload(code="abc", state=None, nonce=LOGIN_NONCE):
    return {"code": code, "state": state or make_login_state(nonce), "nonce": nonce}


@pytest.fixture
def mock_github_login(monkeypatch):
    from core import github

    monkeypatch.setattr(
        github,
        "exchange_oauth_code",
        lambda code, redirect_uri: {"access_token": "gho_login", "scope": "read:user"},
    )
    monkeypatch.setattr(
        github,
        "fetch_authenticated_user",
        lambda token: {
            "id": 9090,
            "login": "octocat",
            "avatar_url": "https://a/o.png",
            "email": "octocat@example.com",
        },
    )


class TestGitHubLogin:
    def test_login_url_is_public(self, api, db, oauth_settings):
        resp = api.get("/api/v1/github/oauth/login-url/")
        assert resp.status_code == 200
        url = resp.data["authorize_url"]
        assert "github.com/login/oauth/authorize" in url
        assert "allow_signup=true" in url

    def test_login_url_unconfigured(self, api, db, settings):
        settings.GITHUB_OAUTH_CLIENT_ID = ""
        resp = api.get("/api/v1/github/oauth/login-url/")
        assert resp.status_code == 503

    def test_login_creates_user_and_returns_tokens(
        self, api, db, oauth_settings, mock_github_login
    ):
        resp = api.post(
            "/api/v1/github/oauth/login/",
            login_payload(),
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["created"] is True
        assert resp.data["username"] == "octocat"
        assert resp.data["access"] and resp.data["refresh"]
        user = User.objects.get(username="octocat")
        assert user.has_usable_password() is False
        assert Profile.objects.filter(user=user).exists()
        account = GitHubAccount.objects.get(user=user)
        assert account.github_id == 9090
        # Stored token decrypts back to the original value.
        assert account.access_token == "gho_login"

    def test_login_existing_account_signs_in_without_duplicate(
        self, api, db, oauth_settings, mock_github_login
    ):
        first = api.post(
            "/api/v1/github/oauth/login/",
            login_payload(),
            format="json",
        )
        assert first.data["created"] is True
        second = api.post(
            "/api/v1/github/oauth/login/",
            login_payload(code="def"),
            format="json",
        )
        assert second.status_code == 200
        assert second.data["created"] is False
        assert User.objects.filter(username__startswith="octocat").count() == 1

    def test_login_username_collision_gets_suffixed(
        self, api, db, oauth_settings, mock_github_login
    ):
        make_user("octocat")
        resp = api.post(
            "/api/v1/github/oauth/login/",
            login_payload(),
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["username"] == "octocat-2"

    def test_unique_username_avoids_reserved(self, db):
        from api.views import _unique_username

        assert _unique_username("settings") == "settings-2"
        assert _unique_username("brandnewdev") == "brandnewdev"

    def test_login_url_returns_nonce(self, api, db, oauth_settings):
        resp = api.get("/api/v1/github/oauth/login-url/")
        assert resp.data["nonce"]
        # The nonce is embedded in the signed state too.
        assert "state=" in resp.data["authorize_url"]

    def test_login_rejects_connect_state(self, api, alice, oauth_settings):
        # A "connect" state must not be usable to sign in (different salt).
        resp = api.post(
            "/api/v1/github/oauth/login/",
            {"code": "abc", "state": make_state(alice), "nonce": "x"},
            format="json",
        )
        assert resp.status_code == 400

    def test_login_rejects_nonce_mismatch(self, api, db, oauth_settings, mock_github_login):
        # State minted for one browser cannot be completed with a different
        # nonce (login CSRF / session-fixation guard).
        resp = api.post(
            "/api/v1/github/oauth/login/",
            {"code": "abc", "state": make_login_state("nonce-A"), "nonce": "nonce-B"},
            format="json",
        )
        assert resp.status_code == 400
        assert not User.objects.filter(username="octocat").exists()

    def test_access_token_is_encrypted_at_rest(self, api, db, oauth_settings, mock_github_login):
        api.post(
            "/api/v1/github/oauth/login/",
            login_payload(),
            format="json",
        )
        # The raw column value (bypassing the field's decryption) is ciphertext.
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT access_token FROM core_githubaccount WHERE github_id = %s", [9090])
            raw = cur.fetchone()[0]
        assert raw != "gho_login"
        from core.encryption import decrypt

        assert decrypt(raw) == "gho_login"

    def test_account_get_and_disconnect(self, auth_alice, alice, oauth_settings):
        resp = auth_alice.get("/api/v1/github/account/")
        assert resp.status_code == 200
        assert resp.data["connected"] is False

        GitHubAccount.objects.create(
            user=alice, github_id=1, login="alice-gh", access_token="gho_x"
        )
        resp = auth_alice.get("/api/v1/github/account/")
        assert resp.data["connected"] is True
        assert resp.data["login"] == "alice-gh"

        resp = auth_alice.delete("/api/v1/github/account/")
        assert resp.status_code == 204
        assert not GitHubAccount.objects.filter(user=alice).exists()

    def test_import_requires_connection(self, auth_alice, oauth_settings):
        resp = auth_alice.post("/api/v1/github/import/")
        assert resp.status_code == 400

    def test_import_caches_repos(self, auth_alice, alice, oauth_settings, monkeypatch):
        from core import github

        GitHubAccount.objects.create(
            user=alice, github_id=1, login="alice-gh", access_token="gho_x"
        )
        monkeypatch.setattr(
            github,
            "list_authenticated_repos",
            lambda token: [sample_repo_payload("alice-gh/widget")],
        )
        resp = auth_alice.post("/api/v1/github/import/")
        assert resp.status_code == 200
        assert resp.data[0]["full_name"] == "alice-gh/widget"
        assert Repo.objects.filter(full_name="alice-gh/widget").exists()


class TestSeedDemo:
    def test_seed_demo_is_idempotent_and_logins_work(self, api, db):
        from django.core.management import call_command

        call_command("seed_demo")
        first_posts = Post.objects.count()
        first_users = User.objects.count()
        assert first_posts > 0
        assert Repo.objects.count() > 10

        # Re-running must not duplicate rows.
        call_command("seed_demo")
        assert Post.objects.count() == first_posts
        assert User.objects.count() == first_users

        # A demo user can authenticate with the documented password.
        resp = api.post(
            "/api/v1/auth/token/",
            {"username": "ada-rs", "password": "Passw0rd!123"},
            format="json",
        )
        assert resp.status_code == 200
