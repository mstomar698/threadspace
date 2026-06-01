import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import Comment, Follow, Post, Profile

User = get_user_model()


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
