"""Seed realistic demo data for manually exercising ThreadSpace.

Creates a handful of (fictional) build-in-public developer accounts, a catalogue
of real, currently-very-active open-source projects, plus devlog posts, follows,
likes, and comments — enough to make the feed, Projects pages, profiles, and
social actions feel populated.

Idempotent: re-running updates/keeps existing rows rather than duplicating.

    python manage.py seed_demo

Repo star/fork counts are approximate (early 2026) and only for demo realism.
The usernames are fictional personas; they post about real projects but do not
represent the real maintainers of those projects.
"""

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_datetime

from core.models import Comment, Follow, GitHubAccount, Like, Post, Profile, Repo

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
    b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

DEMO_PASSWORD = "Passw0rd!123"

# full_name -> metadata for real, highly-active OSS projects (approx, early 2026).
REPOS = {
    "vercel/next.js": (
        "TypeScript",
        "The React Framework.",
        ["react", "ssr", "framework"],
        128000,
        27000,
        2600,
    ),
    "rust-lang/rust": (
        "Rust",
        "Empowering everyone to build reliable and efficient software.",
        ["rust", "compiler"],
        99000,
        12800,
        9700,
    ),
    "pytorch/pytorch": (
        "Python",
        "Tensors and dynamic neural networks with strong GPU acceleration.",
        ["deep-learning", "gpu", "tensor"],
        86000,
        23000,
        15000,
    ),
    "huggingface/transformers": (
        "Python",
        "State-of-the-art ML for PyTorch, TensorFlow, and JAX.",
        ["nlp", "transformers", "llm"],
        139000,
        28000,
        1500,
    ),
    "astral-sh/ruff": (
        "Rust",
        "An extremely fast Python linter and formatter, written in Rust.",
        ["python", "linter", "rust"],
        36000,
        1200,
        1600,
    ),
    "astral-sh/uv": (
        "Rust",
        "An extremely fast Python package and project manager, written in Rust.",
        ["python", "packaging", "rust"],
        38000,
        1100,
        1700,
    ),
    "ollama/ollama": (
        "Go",
        "Get up and running with large language models locally.",
        ["llm", "ai", "go"],
        110000,
        8800,
        1500,
    ),
    "langchain-ai/langchain": (
        "Python",
        "Build context-aware reasoning applications.",
        ["llm", "agents", "ai"],
        99000,
        16000,
        300,
    ),
    "sveltejs/svelte": (
        "TypeScript",
        "Cybernetically enhanced web apps.",
        ["svelte", "framework", "ui"],
        81000,
        4400,
        800,
    ),
    "zed-industries/zed": (
        "Rust",
        "A high-performance, multiplayer code editor.",
        ["editor", "rust", "gpui"],
        56000,
        3700,
        2200,
    ),
    "tokio-rs/tokio": (
        "Rust",
        "An asynchronous runtime for Rust.",
        ["async", "rust", "tokio"],
        28000,
        2600,
        270,
    ),
    "denoland/deno": (
        "Rust",
        "A modern runtime for JavaScript and TypeScript.",
        ["javascript", "typescript", "runtime"],
        102000,
        5600,
        2000,
    ),
}

# Personal demo projects (owned by the demo users), so profile/Projects pages show repos.
PERSONAL_REPOS = {
    "ada-rs/lattice": (
        "Rust",
        "A tiny lock-free data-structure playground.",
        ["rust", "concurrency"],
        412,
        18,
        6,
    ),
    "linh-ml/tinytensor": (
        "Python",
        "A 500-line autograd engine for teaching.",
        ["ml", "autograd"],
        980,
        73,
        11,
    ),
    "marco-web/edge-router": (
        "TypeScript",
        "Type-safe routing for edge runtimes.",
        ["typescript", "edge"],
        1300,
        64,
        22,
    ),
    "sora-ai/promptkit": (
        "Python",
        "Composable prompt templates for LLM apps.",
        ["llm", "prompts"],
        760,
        41,
        9,
    ),
    "kai-dev/lazybuild": (
        "Go",
        "Incremental build orchestrator for monorepos.",
        ["build", "monorepo"],
        540,
        29,
        14,
    ),
}

# username -> (bio, location, github_login, [owned personal full_names], [post (caption, repo_full_name|None)])
USERS = {
    "ada-rs": (
        "Systems + Rust. Chasing data races so you don't have to.",
        "Berlin",
        "ada-rs",
        ["ada-rs/lattice"],
        [
            (
                "Landed a lock-free ring buffer in lattice — 2.3x throughput on the bench. 🦀",
                "ada-rs/lattice",
            ),
            (
                "Spent the day reading ruff's formatter internals. The Rust craftsmanship here is wild.",
                "astral-sh/ruff",
            ),
            (
                "tokio's new task budgeting fixed a latency spike I'd been chasing for weeks.",
                "tokio-rs/tokio",
            ),
        ],
    ),
    "linh-ml": (
        "ML engineer. Teaching deep learning from first principles.",
        "Hanoi",
        "linh-ml",
        ["linh-ml/tinytensor"],
        [
            (
                "tinytensor now does reverse-mode autodiff in ~500 lines. Great for teaching.",
                "linh-ml/tinytensor",
            ),
            (
                "Fine-tuned a small model with transformers today — the Trainer API keeps getting nicer.",
                "huggingface/transformers",
            ),
            (
                "PyTorch's compile path shaved 30% off my training loop. Free speedup.",
                "pytorch/pytorch",
            ),
        ],
    ),
    "marco-web": (
        "Frontend + edge. Shipping fast, typed UIs.",
        "Lisbon",
        "marco-web",
        ["marco-web/edge-router"],
        [
            (
                "edge-router hit 1.0 — fully type-safe params end to end. 🎉",
                "marco-web/edge-router",
            ),
            (
                "Migrated a side project to the Next.js app router. The streaming story is great.",
                "vercel/next.js",
            ),
            (
                "Svelte 5 runes finally clicked for me. Reactivity that just makes sense.",
                "sveltejs/svelte",
            ),
        ],
    ),
    "sora-ai": (
        "Building LLM tooling in public.",
        "Tokyo",
        "sora-ai",
        ["sora-ai/promptkit"],
        [
            (
                "promptkit can now diff two prompt versions and show token deltas.",
                "sora-ai/promptkit",
            ),
            (
                "Running everything locally with ollama now — no more API bills for prototyping.",
                "ollama/ollama",
            ),
            (
                "LangChain's new agent middleware made my pipeline way easier to reason about.",
                "langchain-ai/langchain",
            ),
        ],
    ),
    "kai-dev": (
        "Developer tooling nerd. Make the build faster.",
        "Toronto",
        "kai-dev",
        ["kai-dev/lazybuild"],
        [
            (
                "lazybuild now caches across CI runs — cold builds down from 9m to 90s.",
                "kai-dev/lazybuild",
            ),
            ("Switched our whole repo to uv. Installs are basically instant now.", "astral-sh/uv"),
            (
                "Zed's collaborative editing is the first thing that's tempted me away from my old editor.",
                "zed-industries/zed",
            ),
        ],
    ),
    "nova-go": (
        "Go + distributed systems. Streams all the way down.",
        "Nairobi",
        "nova-go",
        [],
        [
            (
                "Built a tiny durable queue this weekend. Deno's KV made the prototype a breeze.",
                "denoland/deno",
            ),
            (
                "Reading the Rust compiler's MIR docs to understand borrow-checking better.",
                "rust-lang/rust",
            ),
        ],
    ),
}

# (follower, following) edges — a small but connected social graph.
FOLLOWS = [
    ("ada-rs", "kai-dev"),
    ("ada-rs", "nova-go"),
    ("linh-ml", "sora-ai"),
    ("linh-ml", "ada-rs"),
    ("marco-web", "ada-rs"),
    ("marco-web", "sora-ai"),
    ("sora-ai", "linh-ml"),
    ("sora-ai", "marco-web"),
    ("kai-dev", "ada-rs"),
    ("kai-dev", "marco-web"),
    ("nova-go", "ada-rs"),
    ("nova-go", "kai-dev"),
]


class Command(BaseCommand):
    help = "Seed realistic demo users, real OSS projects, posts, follows, likes, and comments."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # 1. Repos (real + personal).
        for full_name, meta in {**REPOS, **PERSONAL_REPOS}.items():
            language, description, topics, stars, forks, issues = meta
            owner, _, name = full_name.partition("/")
            Repo.objects.update_or_create(
                full_name=full_name,
                defaults={
                    "name": name,
                    "owner_login": owner,
                    "owner_avatar_url": f"https://avatars.example/{owner}.png",
                    "html_url": f"https://github.com/{full_name}",
                    "description": description,
                    "language": language,
                    "topics": list(topics),
                    "stargazers_count": stars,
                    "forks_count": forks,
                    "open_issues_count": issues,
                    "pushed_at": parse_datetime("2026-02-15T00:00:00Z"),
                },
            )

        # 2. Users + profiles + linked GitHub accounts.
        users = {}
        for index, (username, (bio, location, gh_login, _owned, _posts)) in enumerate(
            USERS.items()
        ):
            user, _ = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.com"}
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            Profile.objects.update_or_create(user=user, defaults={"bio": bio, "location": location})
            GitHubAccount.objects.update_or_create(
                user=user,
                defaults={
                    # Deterministic, collision-free demo id.
                    "github_id": 900_000 + index,
                    "login": gh_login,
                    "avatar_url": f"https://avatars.example/{gh_login}.png",
                    "access_token": "demo-token",
                },
            )
            users[username] = user

        # 3. Posts (one per entry; guarded by caption to stay idempotent).
        posts_by_user = {}
        for username, (_b, _l, _gh, _owned, posts) in USERS.items():
            user = users[username]
            created = []
            for caption, repo_full_name in posts:
                existing = Post.objects.filter(user=user, caption=caption).first()
                if existing:
                    created.append(existing)
                    continue
                repo = (
                    Repo.objects.filter(full_name=repo_full_name).first()
                    if repo_full_name
                    else None
                )
                post = Post(user=user, caption=caption, repo=repo)
                post.image.save("demo.png", ContentFile(TINY_PNG), save=True)
                created.append(post)
            posts_by_user[username] = created

        # 4. Follows.
        for follower_name, following_name in FOLLOWS:
            Follow.objects.get_or_create(
                follower=users[follower_name], following=users[following_name]
            )

        # 5. Likes — each user likes the posts of people they follow.
        for follower_name, following_name in FOLLOWS:
            for post in posts_by_user.get(following_name, []):
                Like.objects.get_or_create(post=post, user=users[follower_name])

        # 6. A few comments for realism.
        sample_comments = [
            ("kai-dev", "ada-rs", "This is great — mind if I borrow the bench setup?"),
            ("linh-ml", "sora-ai", "promptkit's diff view is exactly what I needed."),
            ("marco-web", "ada-rs", "Lock-free ring buffers scare me, respect. 🙇"),
            ("sora-ai", "marco-web", "Edge routing done right. Starring."),
            ("nova-go", "kai-dev", "90s cold builds is the dream."),
        ]
        for commenter, author, body in sample_comments:
            target = posts_by_user.get(author)
            if target:
                Comment.objects.get_or_create(post=target[0], user=users[commenter], body=body)

        repos = Repo.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo seed complete: {len(users)} users, {repos} repos, "
                f"{Post.objects.count()} posts, {Follow.objects.count()} follows, "
                f"{Like.objects.count()} likes, {Comment.objects.count()} comments."
            )
        )
        self.stdout.write(f"Log in as any of: {', '.join(USERS)} — password: {DEMO_PASSWORD}")
