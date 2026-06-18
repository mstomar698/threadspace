"""Seed project-chat messages and deeply-nested comment threads.

Populates the message UI (per-project chat rooms) and the threaded-reply UI with
realistic multi-user conversations, including comment threads nested up to
``--depth`` levels (default 7). Always includes the ``mstomar698`` user as a
participant. Idempotent: re-running matches existing rows by content.

    python manage.py seed_threads

The fictional demo users are created if missing (password Passw0rd!123);
``mstomar698`` is reused if it already exists (e.g. from a real GitHub login) and
never has its credentials touched.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import ChatMessage, Comment, Post, Profile, Repo

DEMO_PASSWORD = "Passw0rd!123"
OWNER = "mstomar698"
# Participants, in rotation. The owner is first so they appear throughout.
PARTICIPANTS = [OWNER, "ada-rs", "linh-ml", "marco-web", "sora-ai", "kai-dev", "nova-go"]

CHAT_SCRIPT = [
    "anyone around to review the latest PR? 👀",
    "just pushed a fix for the flaky test 🤞",
    "the new build shaved ~20% off cold start",
    "nice — what changed?",
    "swapped the bundler config and lazy-loaded the editor",
    "🔥 merging once CI is green",
    "shipped. thanks all 🙌",
]

THREAD_OPENERS = [
    "Curious how everyone structures their error handling here 🧵",
    "Hot take: most caching bugs are actually invalidation bugs.",
    "What's your go-to for profiling this kind of workload?",
]
THREAD_REPLIES = [
    "Good question — we wrap everything in a Result type.",
    "We lean on structured logging plus tracing spans.",
    "+1, and we alert on the span error rate.",
    "Does that hold up under load though?",
    "Surprisingly yes — the overhead is tiny.",
    "Got benchmarks? Would love to see numbers.",
    "Will drop them in the next devlog 👀",
]

# Text-only posts that @-mention users, so Explore → Mentions has data.
MENTION_POSTS = [
    ("ada-rs", "Huge thanks to @mstomar698 for the thorough code review 🙌"),
    ("kai-dev", "Pairing with @mstomar698 and @ada-rs on the build cache today."),
    ("linh-ml", "@mstomar698 your ranking write-up finally made gravity click for me."),
    ("marco-web", "shoutout to @sora-ai and @mstomar698 for the design feedback ✨"),
]


class Command(BaseCommand):
    help = "Seed chat messages and deeply-nested comment threads (incl. mstomar698)."

    def add_arguments(self, parser):
        parser.add_argument("--depth", type=int, default=7, help="Max thread nesting depth (>= 2).")

    @transaction.atomic
    def handle(self, *args, **opts):
        User = get_user_model()
        depth = max(2, opts["depth"])

        users = []
        for name in PARTICIPANTS:
            user, created = User.objects.get_or_create(
                username=name, defaults={"email": f"{name}@example.com"}
            )
            # Give fresh fictional users a usable password; never touch the owner's
            # credentials (they sign in via GitHub).
            if created and name != OWNER:
                user.set_password(DEMO_PASSWORD)
                user.save()
            Profile.objects.get_or_create(user=user)
            users.append(user)
        owner = users[0]

        # 1. Project chat rooms — multi-user conversations in the top repos.
        rooms = list(Repo.objects.order_by("-stargazers_count", "full_name")[:5])
        chats = 0
        for repo in rooms:
            for i, text in enumerate(CHAT_SCRIPT):
                _, made = ChatMessage.objects.get_or_create(
                    repo=repo, user=users[i % len(users)], body=text
                )
                chats += int(made)

        # 2. Deeply-nested threads on the most recent posts. Exclude @-mention
        # posts (seeded below) so the target set stays stable across re-runs.
        posts = list(
            Post.objects.exclude(caption__icontains="@").order_by("-created_at")[
                : len(THREAD_OPENERS)
            ]
        )
        deepest = 0
        for opener, post in zip(THREAD_OPENERS, posts, strict=False):
            top, _ = Comment.objects.get_or_create(
                post=post, parent=None, user=users[1], body=opener
            )
            node = top
            for level in range(2, depth + 1):
                speaker = users[level % len(users)]
                reply_text = THREAD_REPLIES[(level - 2) % len(THREAD_REPLIES)]
                node, _ = Comment.objects.get_or_create(
                    post=post, parent=node, user=speaker, body=f"{reply_text} (L{level})"
                )
                deepest = max(deepest, level)
            # A side branch off the root so the thread isn't purely linear, with
            # the owner participating.
            Comment.objects.get_or_create(
                post=post,
                parent=top,
                user=owner,
                body="Adding my take here too — great thread. (mstomar698)",
            )

        # 3. A few @-mention posts so Explore → Mentions has content.
        by_name = {u.username: u for u in users}
        mentions = 0
        for author_name, caption in MENTION_POSTS:
            author = by_name.get(author_name)
            if not author:
                continue
            _, made = Post.objects.get_or_create(
                user=author, caption=caption, defaults={"image": None}
            )
            mentions += int(made)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {chats} chat messages across {len(rooms)} rooms, "
                f"threads up to depth {deepest} on {len(posts)} posts, "
                f"and {mentions} @-mention posts."
            )
        )
        self.stdout.write(f"Participants: {', '.join(PARTICIPANTS)}")
