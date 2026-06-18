"""Best-effort client for the Rust realtime gateway.

Django owns the social graph, so it computes each event's audience (the
author's followers) and hands it to the gateway, which fans the event out to
connected WebSocket clients. Publishing is fire-and-forget: the gateway being
slow or down must never break the request that triggered the event.
"""

import json
import logging
import threading
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def _send(url: str, payload: bytes, headers: dict[str, str]) -> None:
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=3):
            pass
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning("realtime publish failed: %s", exc)


def publish_event(event: dict, audience: list[str] | None = None, room: str | None = None) -> None:
    """Publish an activity event to the realtime gateway without blocking.

    ``audience`` targets specific usernames (follower fan-out); ``room`` targets a
    named room (e.g. a project's chat, ``owner/name``). When both are ``None`` the
    event broadcasts to every connected client.

    No-op when ``REALTIME_URL`` is not configured (e.g. local dev / tests).
    """
    base = getattr(settings, "REALTIME_URL", "")
    if not base:
        return

    url = f"{base.rstrip('/')}/internal/publish"
    payload = json.dumps({"audience": audience, "room": room, "event": event}).encode()
    headers = {"Content-Type": "application/json"}
    token = getattr(settings, "REALTIME_INTERNAL_TOKEN", "")
    if token:
        headers["X-Internal-Token"] = token

    # Deliver off the request thread so post creation never waits on socket I/O.
    threading.Thread(target=_send, args=(url, payload, headers), daemon=True).start()
