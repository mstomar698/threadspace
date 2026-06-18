"""Sync a catalogue of the most-starred public GitHub repositories.

Builds/refreshes the ``Repo`` table with the top-N repos by stars so the
composer's project autofill has real data to suggest. GitHub's search API caps
any single query at 1000 results, so we shard by descending star windows
(``stars:min..hi``) and walk the boundary downward until we hit ``--limit``.

    python manage.py sync_top_repos --limit 10000

Needs ``GITHUB_API_TOKEN`` for a usable rate limit (search = 30 req/min
authenticated, 10/min anonymous). Paces requests with ``--sleep`` and backs off
on rate-limit responses. Rows are marked ``source="sync"``.
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand

from core import github
from core.models import Repo

PER_PAGE = 100
MAX_PAGES = 10  # search caps at 1000 results = 10 pages of 100


class Command(BaseCommand):
    help = "Sync the top-N most-starred public repositories into the Repo catalogue."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10000, help="How many repos to sync.")
        parser.add_argument(
            "--min-stars", type=int, default=50, help="Lower star bound to stop at."
        )
        parser.add_argument(
            "--start-stars",
            type=int,
            default=500000,
            help="Upper star bound for the first window.",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=2.1,
            help="Seconds between search requests (≈28/min keeps under the limit).",
        )

    def handle(self, *args, **opts):
        limit = opts["limit"]
        min_stars = opts["min_stars"]
        sleep = opts["sleep"]
        hi = opts["start_stars"]

        token = getattr(settings, "GITHUB_API_TOKEN", "")
        if not token and not getattr(settings, "GITHUB_STUB", False):
            self.stderr.write(
                self.style.WARNING(
                    "No GITHUB_API_TOKEN set — search is limited to ~10 req/min and will be slow."
                )
            )

        seen: set[str] = set()
        while len(seen) < limit and hi >= min_stars:
            query = f"stars:{min_stars}..{hi}"
            window_lowest = hi
            window_count = 0
            page = 1
            while page <= MAX_PAGES and len(seen) < limit:
                try:
                    data = github.search_repositories(query, page=page, token=token)
                except github.RateLimited as exc:
                    self._wait_for_reset(exc.reset_epoch)
                    continue  # retry the same page
                except github.RepoFetchError as exc:
                    self.stderr.write(self.style.ERROR(f"Search failed ({query} p{page}): {exc}"))
                    break

                items = data.get("items") or []
                if not items:
                    break
                for item in items:
                    full_name = item.get("full_name")
                    if not full_name or full_name in seen:
                        continue
                    existing = Repo.objects.filter(full_name__iexact=full_name).first()
                    github._apply_metadata(existing or Repo(), item, source="sync")
                    seen.add(full_name)
                    window_count += 1
                    window_lowest = min(window_lowest, item.get("stargazers_count", window_lowest))
                    if len(seen) >= limit:
                        break

                if len(items) < PER_PAGE:
                    break  # last page of this window
                page += 1
                time.sleep(sleep)

            self.stdout.write(f"stars:{min_stars}..{hi} → +{window_count} (total {len(seen)})")
            if window_count == 0:
                break  # nothing left in or below this window

            # Walk the upper bound down past the lowest star count we just saw.
            next_hi = window_lowest - 1
            hi = next_hi if next_hi < hi else hi - 1
            time.sleep(sleep)

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {len(seen)} repositories (catalogue now {Repo.objects.count()} rows)."
            )
        )

    def _wait_for_reset(self, reset_epoch: int | None) -> None:
        """Sleep until the rate limit resets (or a short default backoff)."""
        delay = 60.0
        if reset_epoch:
            delay = max(1.0, reset_epoch - time.time()) + 1.0
        self.stderr.write(self.style.WARNING(f"Rate limited; sleeping {delay:.0f}s…"))
        time.sleep(delay)
