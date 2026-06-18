from django.contrib import admin

from .models import (
    ChatMessage,
    Comment,
    Follow,
    GitHubAccount,
    Like,
    Post,
    Profile,
    Repo,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "created_at")
    search_fields = ("user__username", "location")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "caption", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "caption")
    autocomplete_fields = ("user",)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    autocomplete_fields = ("user", "post")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    autocomplete_fields = ("follower", "following")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "body", "created_at")
    autocomplete_fields = ("user", "post", "parent")
    search_fields = ("user__username", "body")


@admin.register(Repo)
class RepoAdmin(admin.ModelAdmin):
    list_display = ("full_name", "language", "stargazers_count", "fetched_at")
    search_fields = ("full_name", "description")


@admin.register(GitHubAccount)
class GitHubAccountAdmin(admin.ModelAdmin):
    list_display = ("login", "user", "connected_at")
    search_fields = ("login", "user__username")
    autocomplete_fields = ("user",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("repo", "user", "created_at")
    search_fields = ("repo__full_name", "user__username", "body")
    autocomplete_fields = ("user", "repo")
