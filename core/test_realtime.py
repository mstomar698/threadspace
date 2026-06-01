import json
from unittest import mock

import pytest
from django.test import override_settings

from core import realtime
from core.models import Follow, Post
from core.tests import make_user, tiny_image


@pytest.fixture
def alice(db):
    return make_user("alice")


@pytest.fixture
def bob(db):
    return make_user("bob")


class TestFanout:
    def test_new_post_fans_out_to_followers_and_self(self, alice, bob):
        Follow.objects.create(follower=alice, following=bob)

        with mock.patch("core.signals.publish_event") as publish:
            post = Post.objects.create(user=bob, image=tiny_image(), caption="shipped")

        assert publish.called
        event = publish.call_args.args[0]
        audience = publish.call_args.kwargs["audience"]
        assert set(audience) == {"alice", "bob"}
        assert event["type"] == "post.created"
        assert event["actor"] == "bob"
        assert event["post_id"] == str(post.id)
        assert event["title"] == "shipped"

    def test_update_does_not_publish(self, bob):
        with mock.patch("core.signals.publish_event") as publish:
            post = Post.objects.create(user=bob, image=tiny_image(), caption="x")
            publish.reset_mock()
            post.caption = "y"
            post.save()

        assert not publish.called


class TestPublishEvent:
    @override_settings(REALTIME_URL="")
    def test_noop_without_url(self):
        with mock.patch("core.realtime._send") as send:
            realtime.publish_event({"type": "x", "actor": "a"}, audience=["a"])
        assert not send.called

    @override_settings(REALTIME_URL="http://gw:8080", REALTIME_INTERNAL_TOKEN="secret")
    def test_posts_to_gateway(self):
        class FakeThread:
            def __init__(self, target=None, args=(), daemon=False):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        with (
            mock.patch("core.realtime.threading.Thread", FakeThread),
            mock.patch("core.realtime._send") as send,
        ):
            realtime.publish_event({"type": "post.created", "actor": "a"}, audience=["a", "b"])

        assert send.called
        url, payload, headers = send.call_args.args
        assert url == "http://gw:8080/internal/publish"
        assert headers["X-Internal-Token"] == "secret"
        body = json.loads(payload)
        assert body["audience"] == ["a", "b"]
        assert body["event"]["type"] == "post.created"
