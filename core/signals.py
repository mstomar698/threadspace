"""Signal handlers that emit realtime activity events."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Follow, Post
from .realtime import publish_event


@receiver(post_save, sender=Post)
def broadcast_new_post(sender, instance: Post, created, **kwargs):
    """Fan a freshly created post out to the author's followers (and self)."""
    if not created:
        return

    author = instance.user
    audience = list(
        Follow.objects.filter(following=author).values_list("follower__username", flat=True)
    )
    audience.append(author.username)

    event = {
        "type": "post.created",
        "actor": author.username,
        "title": (instance.caption or "shared a new post").strip()[:140],
        "post_id": str(instance.id),
        "repo": instance.repo.full_name if instance.repo_id else None,
        "created_at": instance.created_at.isoformat(),
    }
    publish_event(event, audience=audience)
