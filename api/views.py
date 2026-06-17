from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core import github
from core.github import RepoFetchError, RepoNotFound, get_or_refresh_repo
from core.models import Comment, Follow, GitHubAccount, Like, Post, Profile

from .pagination import FeedCursorPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    CommentSerializer,
    GitHubAccountSerializer,
    GithubOAuthCallbackSerializer,
    PostSerializer,
    ProfileSerializer,
    RegisterSerializer,
    RepoResolveSerializer,
    RepoSerializer,
)

User = get_user_model()

GITHUB_OAUTH_SALT = "github-oauth-state"
GITHUB_LOGIN_SALT = "github-oauth-login"


def _oauth_redirect_uri():
    from django.conf import settings

    return f"{settings.FRONTEND_URL.rstrip('/')}/github/callback"


def _unique_username(base: str) -> str:
    """Return a username based on ``base`` that no existing user holds."""
    base = (base or "").strip() or "dev"
    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


@transaction.atomic
def _login_or_create_user(gh_user, token_payload):
    """Find the user linked to this GitHub identity, or create one.

    Returns ``(user, created)``. New users sign in via GitHub only and get an
    unusable password until they set one.
    """
    github_id = gh_user["id"]
    defaults = {
        "login": gh_user.get("login", ""),
        "avatar_url": gh_user.get("avatar_url", "") or "",
        "access_token": token_payload["access_token"],
        "scopes": token_payload.get("scope", ""),
    }
    account = GitHubAccount.objects.filter(github_id=github_id).select_related("user").first()
    if account:
        for key, value in defaults.items():
            setattr(account, key, value)
        account.save()
        return account.user, False

    user = User(username=_unique_username(gh_user.get("login")), email=gh_user.get("email") or "")
    user.set_unusable_password()
    user.save()
    Profile.objects.create(user=user)
    GitHubAccount.objects.create(user=user, github_id=github_id, **defaults)
    return user, True


def _resolve_repo_response(identifier):
    """Shared resolve logic returning a DRF Response (repo data or error)."""
    try:
        repo = get_or_refresh_repo(identifier)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except RepoNotFound:
        return Response(
            {"detail": "Repository not found on GitHub."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except RepoFetchError:
        return Response(
            {"detail": "Could not reach GitHub, try again."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(RepoSerializer(repo).data)


class GithubResolveView(APIView):
    """Resolve a GitHub URL or owner/name into enriched repo metadata."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=RepoResolveSerializer, responses=RepoSerializer)
    def post(self, request):
        return _resolve_repo_response(request.data.get("q", ""))


class RepoDetailView(APIView):
    """Project page data: enriched metadata for owner/name."""

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @extend_schema(responses=RepoSerializer)
    def get(self, request, owner, name):
        return _resolve_repo_response(f"{owner}/{name}")


class GithubAuthorizeURLView(APIView):
    """Return the GitHub OAuth authorize URL for the current user to visit."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=OpenApiResponse(description="{'authorize_url': str}"))
    def get(self, request):
        from django.conf import settings

        if not settings.GITHUB_OAUTH_CLIENT_ID:
            return Response(
                {"detail": "GitHub OAuth is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        state = signing.dumps({"uid": request.user.id}, salt=GITHUB_OAUTH_SALT)
        url = github.build_authorize_url(state, _oauth_redirect_uri())
        return Response({"authorize_url": url})


class GithubOAuthCallbackView(APIView):
    """Exchange the OAuth code for a token and link the GitHub account."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GithubOAuthCallbackSerializer, responses=GitHubAccountSerializer)
    def post(self, request):
        serializer = GithubOAuthCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = signing.loads(
                serializer.validated_data["state"], salt=GITHUB_OAUTH_SALT, max_age=600
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Invalid or expired OAuth state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payload.get("uid") != request.user.id:
            return Response(
                {"detail": "OAuth state does not match the current user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token_payload = github.exchange_oauth_code(
                serializer.validated_data["code"], _oauth_redirect_uri()
            )
            gh_user = github.fetch_authenticated_user(token_payload["access_token"])
        except github.OAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        account, _ = GitHubAccount.objects.update_or_create(
            user=request.user,
            defaults={
                "github_id": gh_user["id"],
                "login": gh_user.get("login", ""),
                "avatar_url": gh_user.get("avatar_url", "") or "",
                "access_token": token_payload["access_token"],
                "scopes": token_payload.get("scope", ""),
            },
        )
        return Response(GitHubAccountSerializer(account).data)


class GithubLoginAuthorizeURLView(APIView):
    """Return the GitHub OAuth authorize URL for signing in or signing up."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiResponse(description="{'authorize_url': str}"))
    def get(self, request):
        from django.conf import settings

        if not settings.GITHUB_OAUTH_CLIENT_ID:
            return Response(
                {"detail": "GitHub OAuth is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        state = signing.dumps({"flow": "login"}, salt=GITHUB_LOGIN_SALT)
        url = github.build_authorize_url(state, _oauth_redirect_uri(), allow_signup=True)
        return Response({"authorize_url": url})


class GithubLoginCallbackView(APIView):
    """Sign a user in via GitHub, creating their account on first sign-in."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=GithubOAuthCallbackSerializer,
        responses=OpenApiResponse(
            description="{'access': str, 'refresh': str, 'username': str, 'created': bool}"
        ),
    )
    def post(self, request):
        serializer = GithubOAuthCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = signing.loads(
                serializer.validated_data["state"], salt=GITHUB_LOGIN_SALT, max_age=600
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Invalid or expired OAuth state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payload.get("flow") != "login":
            return Response({"detail": "Invalid OAuth state."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_payload = github.exchange_oauth_code(
                serializer.validated_data["code"], _oauth_redirect_uri()
            )
            gh_user = github.fetch_authenticated_user(token_payload["access_token"])
        except github.OAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        user, created = _login_or_create_user(gh_user, token_payload)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "created": created,
            }
        )


class GithubAccountView(APIView):
    """Read or disconnect the current user's linked GitHub account."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=OpenApiResponse(description="{'connected': bool, ...account}"))
    def get(self, request):
        account = GitHubAccount.objects.filter(user=request.user).first()
        if not account:
            return Response({"connected": False})
        return Response({"connected": True, **GitHubAccountSerializer(account).data})

    @extend_schema(responses={204: None})
    def delete(self, request):
        GitHubAccount.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GithubImportView(APIView):
    """Import (cache/refresh) the connected user's GitHub repositories."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=RepoSerializer(many=True))
    def post(self, request):
        account = GitHubAccount.objects.filter(user=request.user).first()
        if not account:
            return Response(
                {"detail": "Connect your GitHub account first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            repos = github.import_user_repos(account.access_token)
        except github.OAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RepoFetchError:
            return Response(
                {"detail": "Could not reach GitHub, try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(RepoSerializer(repos, many=True).data)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    queryset = User.objects.all()


class MeView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's own profile."""

    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Profile.objects.select_related("user").get(user=self.request.user)


class ProfileViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ProfileSerializer
    lookup_field = "user__username"
    lookup_url_kwarg = "username"
    search_fields = ["user__username", "bio"]

    def get_queryset(self):
        user = self.request.user
        qs = Profile.objects.select_related("user").annotate(
            followers_count=Count("user__followers", distinct=True),
            following_count=Count("user__following", distinct=True),
            posts_count=Count("user__posts", distinct=True),
        )
        if user.is_authenticated:
            qs = qs.annotate(
                is_following=Exists(
                    Follow.objects.filter(follower=user, following=OuterRef("user"))
                )
            )
        return qs.order_by("user__username")

    @extend_schema(
        request=None,
        responses=OpenApiResponse(description="{'following': bool}"),
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, username=None):
        target = self.get_object().user
        if target == request.user:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = Follow.objects.filter(follower=request.user, following=target).first()
        if existing:
            existing.delete()
            return Response({"following": False})
        Follow.objects.create(follower=request.user, following=target)
        return Response({"following": True})

    @action(detail=True, methods=["get"])
    def followers(self, request, username=None):
        target = self.get_object().user
        profiles = self.get_queryset().filter(user__following__following=target)
        page = self.paginate_queryset(profiles)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"])
    def following(self, request, username=None):
        target = self.get_object().user
        profiles = self.get_queryset().filter(user__followers__follower=target)
        page = self.paginate_queryset(profiles)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ["caption", "user__username"]

    def get_queryset(self):
        user = self.request.user
        qs = Post.objects.select_related("user", "user__profile", "repo").annotate(
            num_likes=Count("likes", distinct=True),
            comments_count=Count("comments", distinct=True),
        )
        if user.is_authenticated:
            qs = qs.annotate(liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user)))
        author = self.request.query_params.get("author")
        if author:
            qs = qs.filter(user__username=author)
        repo = self.request.query_params.get("repo")
        if repo:
            qs = qs.filter(repo__full_name__iexact=repo)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=False,
        permission_classes=[permissions.IsAuthenticated],
        pagination_class=FeedCursorPagination,
    )
    def feed(self, request):
        following_ids = Follow.objects.filter(follower=request.user).values_list(
            "following_id", flat=True
        )
        qs = self.get_queryset().filter(Q(user_id__in=following_ids) | Q(user=request.user))
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=None,
        responses=OpenApiResponse(description="{'liked': bool, 'num_likes': int}"),
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
        return Response({"liked": created, "num_likes": post.likes.count()})


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = Comment.objects.select_related("user", "user__profile")
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
