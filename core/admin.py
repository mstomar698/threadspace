from django.contrib import admin

from .models import Comment, Follow, Like, Post, Profile


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
