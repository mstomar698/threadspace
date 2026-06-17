"""Seed deterministic data for the Playwright e2e stack.

Idempotent: safe to run repeatedly. Used by frontend/e2e/backend.sh before the
test server starts. Creates a known maker with a project and a devlog post so
the social, search, profile, and project flows have something to assert on.
"""

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from core.models import GitHubAccount, Post, Profile, Repo

# A 1x1 PNG, enough to satisfy the required Post.image field.
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
    b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

MAKER_PASSWORD = "Passw0rd!123"


class Command(BaseCommand):
    help = "Seed deterministic data for Playwright e2e tests."

    def handle(self, *args, **options):
        User = get_user_model()

        maker, _ = User.objects.get_or_create(
            username="maker", defaults={"email": "maker@example.com"}
        )
        maker.set_password(MAKER_PASSWORD)
        maker.save()
        Profile.objects.get_or_create(
            user=maker,
            defaults={"bio": "I build in public.", "location": "Internet"},
        )
        GitHubAccount.objects.get_or_create(
            user=maker,
            defaults={"github_id": 1, "login": "maker", "access_token": "seed-token"},
        )

        repo, _ = Repo.objects.get_or_create(
            full_name="maker/coolproject",
            defaults={
                "name": "coolproject",
                "owner_login": "maker",
                "html_url": "https://github.com/maker/coolproject",
                "description": "A delightfully cool open-source project.",
                "language": "TypeScript",
                "topics": ["cli", "devtools"],
                "stargazers_count": 128,
                "forks_count": 9,
                "open_issues_count": 4,
                "pushed_at": parse_datetime("2026-02-01T00:00:00Z"),
            },
        )

        if not Post.objects.filter(user=maker).exists():
            post = Post(
                user=maker,
                caption="Shipped the first cut of coolproject 🚀",
                repo=repo,
            )
            post.image.save("seed.png", ContentFile(TINY_PNG), save=True)

        self.stdout.write(self.style.SUCCESS("e2e seed complete"))
