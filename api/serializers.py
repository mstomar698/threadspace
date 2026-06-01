from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from core.github import (
    RepoFetchError,
    RepoNotFound,
    get_or_refresh_repo,
)
from core.models import Comment, Follow, Like, Post, Profile, Repo

User = get_user_model()


class RepoResolveSerializer(serializers.Serializer):
    q = serializers.CharField(help_text="A GitHub repo URL or 'owner/name'.")


class RepoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repo
        fields = [
            "full_name",
            "name",
            "owner_login",
            "owner_avatar_url",
            "html_url",
            "description",
            "homepage",
            "language",
            "topics",
            "stargazers_count",
            "forks_count",
            "open_issues_count",
            "pushed_at",
        ]


class AuthorSerializer(serializers.ModelSerializer):
    profileimg = serializers.ImageField(source="profile.profileimg", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "profileimg"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Profile.objects.create(user=user)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "username",
            "bio",
            "location",
            "profileimg",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_followers_count(self, obj) -> int:
        if hasattr(obj, "followers_count"):
            return obj.followers_count
        return obj.user.followers.count()

    def get_following_count(self, obj) -> int:
        if hasattr(obj, "following_count"):
            return obj.following_count
        return obj.user.following.count()

    def get_posts_count(self, obj) -> int:
        if hasattr(obj, "posts_count"):
            return obj.posts_count
        return obj.user.posts.count()

    def get_is_following(self, obj) -> bool:
        if hasattr(obj, "is_following"):
            return bool(obj.is_following)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Follow.objects.filter(follower=request.user, following=obj.user).exists()


class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    repo = RepoSerializer(read_only=True)
    repo_full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    num_likes = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "caption",
            "image",
            "repo",
            "repo_full_name",
            "created_at",
            "num_likes",
            "comments_count",
            "liked",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        full_name = (validated_data.pop("repo_full_name", "") or "").strip()
        if full_name:
            try:
                validated_data["repo"] = get_or_refresh_repo(full_name)
            except ValueError as exc:
                raise serializers.ValidationError({"repo_full_name": str(exc)}) from exc
            except RepoNotFound as exc:
                raise serializers.ValidationError(
                    {"repo_full_name": "Repository not found on GitHub."}
                ) from exc
            except RepoFetchError as exc:
                raise serializers.ValidationError(
                    {"repo_full_name": "Could not reach GitHub, try again."}
                ) from exc
        return super().create(validated_data)

    def get_num_likes(self, obj) -> int:
        if hasattr(obj, "num_likes"):
            return obj.num_likes
        return obj.likes.count()

    def get_comments_count(self, obj) -> int:
        if hasattr(obj, "comments_count"):
            return obj.comments_count
        return obj.comments.count()

    def get_liked(self, obj) -> bool:
        if hasattr(obj, "liked"):
            return bool(obj.liked)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Like.objects.filter(post=obj, user=request.user).exists()


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Comment
        fields = ["id", "post", "parent", "author", "body", "created_at"]
        read_only_fields = ["id", "created_at"]
