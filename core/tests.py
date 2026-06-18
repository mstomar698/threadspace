import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.urls import reverse

from core.models import Follow, Like, Post, Profile, Repo

User = get_user_model()


def make_user(username, password="testpass123!"):
    user = User.objects.create_user(username=username, password=password)
    Profile.objects.create(user=user)
    return user


def tiny_image(name="t.png"):
    # 1x1 transparent PNG.
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return SimpleUploadedFile(name, io.BytesIO(data).read(), content_type="image/png")


@pytest.fixture
def alice(db):
    return make_user("alice")


@pytest.fixture
def bob(db):
    return make_user("bob")


class TestModels:
    def test_profile_str_is_username(self, alice):
        assert str(alice.profile) == "alice"

    def test_duplicate_like_is_rejected(self, db, alice, bob):
        post = Post.objects.create(user=bob, image=tiny_image(), caption="hi")
        Like.objects.create(post=post, user=alice)
        with pytest.raises(IntegrityError):
            Like.objects.create(post=post, user=alice)

    def test_self_follow_is_rejected(self, alice):
        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=alice, following=alice)

    def test_duplicate_follow_is_rejected(self, alice, bob):
        Follow.objects.create(follower=alice, following=bob)
        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=alice, following=bob)


class TestViews:
    def test_like_toggle_via_post(self, client, alice, bob):
        post = Post.objects.create(user=bob, image=tiny_image(), caption="hi")
        client.force_login(alice)

        client.post(reverse("like-post"), {"post_id": str(post.id)})
        assert Like.objects.filter(post=post, user=alice).count() == 1

        client.post(reverse("like-post"), {"post_id": str(post.id)})
        assert Like.objects.filter(post=post, user=alice).count() == 0

    def test_like_via_get_is_not_allowed(self, client, alice, bob):
        post = Post.objects.create(user=bob, image=tiny_image(), caption="hi")
        client.force_login(alice)
        resp = client.get(reverse("like-post"), {"post_id": str(post.id)})
        assert resp.status_code == 405

    def test_feed_shows_only_followed_users_posts(self, client, alice, bob):
        carol = make_user("carol")
        followed_post = Post.objects.create(user=bob, image=tiny_image(), caption="seen")
        Post.objects.create(user=carol, image=tiny_image(), caption="hidden")
        Follow.objects.create(follower=alice, following=bob)

        client.force_login(alice)
        resp = client.get(reverse("index"))
        feed_ids = {p.id for p in resp.context["posts"]}
        assert followed_post.id in feed_ids
        assert len(feed_ids) == 1

    def test_follow_toggle_via_post(self, client, alice, bob):
        client.force_login(alice)

        client.post(reverse("follow"), {"user": "bob"})
        assert Follow.objects.filter(follower=alice, following=bob).exists()

        client.post(reverse("follow"), {"user": "bob"})
        assert not Follow.objects.filter(follower=alice, following=bob).exists()

    def test_signup_creates_user_and_profile(self, client, db):
        client.post(
            reverse("signup"),
            {
                "username": "dave",
                "email": "dave@example.com",
                "password": "testpass123!",
                "password2": "testpass123!",
            },
        )
        user = User.objects.get(username="dave")
        assert Profile.objects.filter(user=user).exists()

    def test_anonymous_is_redirected_to_signin(self, client, db):
        resp = client.get(reverse("index"))
        assert resp.status_code == 302
        assert "signin" in resp.url


class TestSyncTopRepos:
    def _catalogue(self):
        return [
            {
                "full_name": f"owner{i}/repo{i}",
                "name": f"repo{i}",
                "owner": {"login": f"owner{i}", "avatar_url": "https://a.example/x.png"},
                "html_url": f"https://github.com/owner{i}/repo{i}",
                "description": f"Repo {i}",
                "language": "Python",
                "topics": [],
                "stargazers_count": stars,
                "forks_count": 1,
                "open_issues_count": 1,
                "pushed_at": "2026-01-01T00:00:00Z",
            }
            for i, stars in enumerate([900, 800, 700, 600, 500])
        ]

    def _fake_search(self, catalogue):
        def fake(query, page=1, per_page=100, token=""):
            # query is "stars:LO..HI"
            stars_part = query.split(":", 1)[1]
            lo, hi = (int(x) for x in stars_part.split(".."))
            matches = sorted(
                (r for r in catalogue if lo <= r["stargazers_count"] <= hi),
                key=lambda r: -r["stargazers_count"],
            )
            start = (page - 1) * per_page
            return {"total_count": len(matches), "items": matches[start : start + per_page]}

        return fake

    def test_syncs_and_marks_source(self, db, monkeypatch):
        from django.core.management import call_command

        from core import github

        monkeypatch.setattr(github, "search_repositories", self._fake_search(self._catalogue()))
        call_command("sync_top_repos", "--limit", "5", "--start-stars", "1000", "--sleep", "0")

        assert Repo.objects.count() == 5
        assert Repo.objects.filter(source="sync").count() == 5
        assert Repo.objects.order_by("-stargazers_count").first().full_name == "owner0/repo0"

    def test_respects_limit(self, db, monkeypatch):
        from django.core.management import call_command

        from core import github

        monkeypatch.setattr(github, "search_repositories", self._fake_search(self._catalogue()))
        call_command("sync_top_repos", "--limit", "3", "--start-stars", "1000", "--sleep", "0")
        assert Repo.objects.count() == 3

    def test_idempotent(self, db, monkeypatch):
        from django.core.management import call_command

        from core import github

        monkeypatch.setattr(github, "search_repositories", self._fake_search(self._catalogue()))
        call_command("sync_top_repos", "--limit", "5", "--start-stars", "1000", "--sleep", "0")
        call_command("sync_top_repos", "--limit", "5", "--start-stars", "1000", "--sleep", "0")
        assert Repo.objects.count() == 5
