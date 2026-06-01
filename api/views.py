from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Comment, Follow, Like, Post, Profile

from .pagination import FeedCursorPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    CommentSerializer,
    PostSerializer,
    ProfileSerializer,
    RegisterSerializer,
)

User = get_user_model()


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
        qs = Post.objects.select_related("user", "user__profile").annotate(
            num_likes=Count("likes", distinct=True),
            comments_count=Count("comments", distinct=True),
        )
        if user.is_authenticated:
            qs = qs.annotate(liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user)))
        return qs

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
