from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from core.constants import is_reserved_username
from core.github import (
    RepoFetchError,
    RepoNotFound,
    get_or_refresh_repo,
)
from core.models import (
    ChatMessage,
    Comment,
    Follow,
    GitHubAccount,
    Like,
    Post,
    Profile,
    Repo,
)

User = get_user_model()

# How deeply comment threads may nest (root comment = level 1). Mirrored in the
# frontend (comment-section.tsx).
MAX_THREAD_DEPTH = 7


class RepoResolveSerializer(serializers.Serializer):
    q = serializers.CharField(help_text="A GitHub repo URL or 'owner/name'.")


class GitHubAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubAccount
        fields = ["login", "avatar_url", "scopes", "connected_at"]


class GithubOAuthCallbackSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField()


class GithubLoginCallbackSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField()
    # Echoes the nonce the SPA stored when it started the flow; binds the OAuth
    # state to the initiating browser to prevent login CSRF / session fixation.
    nonce = serializers.CharField()


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


class RepoSuggestSerializer(serializers.ModelSerializer):
    """Slim repo shape for the composer's autofill dropdown."""

    class Meta:
        model = Repo
        fields = [
            "full_name",
            "name",
            "owner_login",
            "description",
            "language",
            "stargazers_count",
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

    def validate_username(self, value):
        if is_reserved_username(value):
            raise serializers.ValidationError("This username is reserved.")
        return value

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
    github_login = serializers.SerializerMethodField()

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
            "github_login",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_github_login(self, obj) -> str | None:
        account = getattr(obj.user, "github", None)
        return account.login if account else None

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

    def validate(self, attrs):
        # A devlog can be text-only, repo-only, or include an image — but it must
        # carry at least one of the three so we never store an empty post.
        has_image = bool(attrs.get("image"))
        has_caption = bool((attrs.get("caption") or "").strip())
        has_repo = bool((attrs.get("repo_full_name") or "").strip())
        if not (has_image or has_caption or has_repo):
            raise serializers.ValidationError(
                "Add a caption, attach a repository, or include an image."
            )
        return attrs

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
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "parent", "author", "body", "replies_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_replies_count(self, obj) -> int:
        if hasattr(obj, "replies_count"):
            return obj.replies_count
        return obj.replies.count()

    def validate(self, attrs):
        parent = attrs.get("parent")
        if parent is not None:
            post = attrs.get("post")
            if post is not None and parent.post_id != post.id:
                raise serializers.ValidationError(
                    {"parent": "Parent comment belongs to a different post."}
                )
            # Threads nest up to MAX_THREAD_DEPTH levels (root comment = level 1).
            depth = 1  # parent's own depth
            node = parent
            while node.parent_id:
                node = node.parent
                depth += 1
            if depth + 1 > MAX_THREAD_DEPTH:
                raise serializers.ValidationError(
                    {"parent": f"Replies can nest at most {MAX_THREAD_DEPTH} levels deep."}
                )
        return attrs


class ChatMessageSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "author", "body", "created_at"]
        read_only_fields = ["id", "created_at"]
