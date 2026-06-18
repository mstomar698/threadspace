from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    CommentViewSet,
    GithubAccountView,
    GithubAuthorizeURLView,
    GithubImportView,
    GithubLoginAuthorizeURLView,
    GithubLoginCallbackView,
    GithubOAuthCallbackView,
    GithubResolveView,
    MeView,
    PostViewSet,
    ProfileViewSet,
    RegisterView,
    RepoChatView,
    RepoDetailView,
    RepoListView,
    RepoSuggestView,
)

router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")

auth_patterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

github_patterns = [
    path("resolve/", GithubResolveView.as_view(), name="github-resolve"),
    path("repos/", RepoListView.as_view(), name="repo-list"),
    path("repos/suggest/", RepoSuggestView.as_view(), name="repo-suggest"),
    path("repos/<str:owner>/<str:name>/", RepoDetailView.as_view(), name="repo-detail"),
    path("repos/<str:owner>/<str:name>/chat/", RepoChatView.as_view(), name="repo-chat"),
    path(
        "oauth/authorize-url/",
        GithubAuthorizeURLView.as_view(),
        name="github-authorize-url",
    ),
    path("oauth/callback/", GithubOAuthCallbackView.as_view(), name="github-callback"),
    path(
        "oauth/login-url/",
        GithubLoginAuthorizeURLView.as_view(),
        name="github-login-url",
    ),
    path("oauth/login/", GithubLoginCallbackView.as_view(), name="github-login"),
    path("account/", GithubAccountView.as_view(), name="github-account"),
    path("import/", GithubImportView.as_view(), name="github-import"),
]

urlpatterns = [
    path("v1/auth/", include(auth_patterns)),
    path("v1/github/", include(github_patterns)),
    path("v1/", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
