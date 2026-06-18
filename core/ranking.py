"""Feed ranking — a time-decayed engagement score.

Posts are ranked by a Hacker News / Reddit-style "hot" score that blends three
signals every social feed cares about:

  * recency   — newer posts start higher and decay over time (gravity),
  * trending  — likes lift a post,
  * activity  — comments lift it more (a conversation signals more activity).

    score = (likes·W_LIKE + comments·W_COMMENT + W_BASE) / (age_hours + OFFSET) ** GRAVITY

A brand-new post with no engagement still scores ~W_BASE/OFFSET**GRAVITY, so the
freshest builds surface immediately; engagement then keeps a post near the top as
it ages, and the gravity term lets it fall off once activity cools. Tuning the
weights/gravity changes how aggressively the feed favours fresh vs. popular.

Computed in Python over a bounded candidate window so the behaviour is identical
on SQLite (dev/tests) and Postgres (prod) without backend-specific SQL math.
"""

from datetime import datetime

# Engagement weights. Comments are weighted above likes because a reply is a
# stronger activity signal than a like.
W_LIKE = 1.0
W_COMMENT = 2.0
# Base weight so a zero-engagement post still has a non-zero, recency-driven score.
W_BASE = 1.0
# Gravity: how fast a post decays with age (higher = recency matters more).
GRAVITY = 1.5
# Hours added to age so very fresh posts don't get an unbounded score spike.
OFFSET_HOURS = 2.0


def hot_score(num_likes: int, comments_count: int, created_at: datetime, now: datetime) -> float:
    """Return the feed ranking score for a single post (higher ranks first)."""
    age_hours = max((now - created_at).total_seconds() / 3600.0, 0.0)
    engagement = num_likes * W_LIKE + comments_count * W_COMMENT + W_BASE
    return engagement / (age_hours + OFFSET_HOURS) ** GRAVITY


def rank_posts(posts, now: datetime):
    """Sort an iterable of annotated Post objects by score (then recency).

    Each post must carry ``num_likes`` and ``comments_count`` (the feed queryset
    annotates these). Sorting is stable and deterministic for a fixed ``now``.
    """
    return sorted(
        posts,
        key=lambda p: (
            hot_score(p.num_likes, p.comments_count, p.created_at, now),
            p.created_at,
        ),
        reverse=True,
    )
