import uuid

from django.conf import settings
from django.db import models

from .fields import EncryptedCharField

User = settings.AUTH_USER_MODEL


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True)
    profileimg = models.ImageField(upload_to="profile_images", default="blank-profile-picture.png")
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.user.username


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    image = models.ImageField(upload_to="post_images")
    caption = models.TextField(blank=True)
    repo = models.ForeignKey(
        "Repo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.caption[:30]}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_like_per_user"),
        ]
        indexes = [models.Index(fields=["post"])]

    def __str__(self):
        return f"{self.user} likes {self.post_id}"


class Repo(models.Model):
    """Cached, enriched metadata for a GitHub repository (a 'project')."""

    full_name = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=120)
    owner_login = models.CharField(max_length=120)
    owner_avatar_url = models.URLField(blank=True)
    html_url = models.URLField()
    description = models.TextField(blank=True)
    homepage = models.URLField(blank=True)
    language = models.CharField(max_length=60, blank=True)
    topics = models.JSONField(default=list, blank=True)
    stargazers_count = models.IntegerField(default=0)
    forks_count = models.IntegerField(default=0)
    open_issues_count = models.IntegerField(default=0)
    pushed_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "created_at"])]

    def __str__(self):
        return f"{self.user.username}: {self.body[:30]}"


class GitHubAccount(models.Model):
    """A ThreadSpace user's linked GitHub account (via OAuth)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="github")
    github_id = models.BigIntegerField(unique=True)
    login = models.CharField(max_length=120)
    avatar_url = models.URLField(blank=True)
    access_token = EncryptedCharField(max_length=500)
    scopes = models.CharField(max_length=255, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.login} ({self.user})"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow_pair"),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("following")),
                name="prevent_self_follow",
            ),
        ]

    def __str__(self):
        return f"{self.follower} -> {self.following}"
