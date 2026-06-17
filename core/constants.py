"""Shared constants."""

# Usernames that collide with frontend top-level routes (which take precedence
# over the dynamic /[username] profile route) or are otherwise reserved. Kept in
# sync with the Next.js app's static routes so a profile is never shadowed.
RESERVED_USERNAMES = frozenset(
    {
        "admin",
        "api",
        "github",
        "login",
        "logout",
        "me",
        "media",
        "projects",
        "register",
        "search",
        "settings",
        "static",
    }
)


def is_reserved_username(username: str) -> bool:
    return (username or "").strip().lower() in RESERVED_USERNAMES
