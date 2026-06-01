from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Follow, Like, Post, Profile

User = get_user_model()


@login_required(login_url="signin")
def index(request):
    user_profile = get_object_or_404(Profile, user=request.user)

    following_ids = Follow.objects.filter(follower=request.user).values_list(
        "following_id", flat=True
    )

    posts = (
        Post.objects.filter(user_id__in=following_ids)
        .select_related("user", "user__profile")
        .annotate(num_likes=Count("likes"))
    )

    suggestions = (
        Profile.objects.exclude(user=request.user)
        .exclude(user_id__in=following_ids)
        .select_related("user")
        .order_by("?")[:4]
    )

    return render(
        request,
        "index.html",
        {
            "user_profile": user_profile,
            "posts": posts,
            "suggestions_username_profile_list": suggestions,
        },
    )


@login_required(login_url="signin")
@require_POST
def upload(request):
    image = request.FILES.get("image_upload")
    caption = request.POST.get("caption", "")

    if image:
        Post.objects.create(user=request.user, image=image, caption=caption)

    return redirect("index")


@login_required(login_url="signin")
def search(request):
    user_profile = get_object_or_404(Profile, user=request.user)

    results = Profile.objects.none()
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if username:
            results = Profile.objects.filter(user__username__icontains=username).select_related(
                "user"
            )

    return render(
        request,
        "search.html",
        {"user_profile": user_profile, "username_profile_list": results},
    )


@login_required(login_url="signin")
@require_POST
def like_post(request):
    post = get_object_or_404(Post, id=request.POST.get("post_id"))

    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()

    return redirect("index")


@login_required(login_url="signin")
def profile(request, pk):
    user_object = get_object_or_404(User, username=pk)
    user_profile = get_object_or_404(Profile, user=user_object)
    user_posts = user_object.posts.all()

    is_following = Follow.objects.filter(follower=request.user, following=user_object).exists()

    context = {
        "user_object": user_object,
        "user_profile": user_profile,
        "user_posts": user_posts,
        "user_post_length": user_posts.count(),
        "button_text": "Unfollow" if is_following else "Follow",
        "user_followers": user_object.followers.count(),
        "user_following": user_object.following.count(),
    }
    return render(request, "profile.html", context)


@login_required(login_url="signin")
@require_POST
def follow(request):
    target = get_object_or_404(User, username=request.POST.get("user"))

    if target == request.user:
        return redirect("profile", pk=target.username)

    existing = Follow.objects.filter(follower=request.user, following=target).first()
    if existing:
        existing.delete()
    else:
        Follow.objects.create(follower=request.user, following=target)

    return redirect("profile", pk=target.username)


@login_required(login_url="signin")
def settings(request):
    user_profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        user_profile.bio = request.POST.get("bio", user_profile.bio)
        user_profile.location = request.POST.get("location", user_profile.location)

        image = request.FILES.get("image")
        if image:
            user_profile.profileimg = image

        user_profile.save()
        messages.success(request, "Profile updated.")
        return redirect("settings")

    return render(request, "setting.html", {"user_profile": user_profile})


def signup(request):
    if request.method != "POST":
        return render(request, "signup.html")

    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    password2 = request.POST.get("password2", "")

    if password != password2:
        messages.info(request, "Password does not match")
        return redirect("signup")

    if User.objects.filter(email=email).exists():
        messages.info(request, "Email already in use!")
        return redirect("signup")

    if User.objects.filter(username=username).exists():
        messages.info(request, "Username not available")
        return redirect("signup")

    try:
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(user=user)
    except IntegrityError:
        messages.info(request, "Could not create account, please try again.")
        return redirect("signup")

    auth_login(request, user)
    return redirect("settings")


def signin(request):
    if request.method != "POST":
        return render(request, "signin.html")

    username = request.POST.get("username", "")
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)

    if user is not None:
        auth_login(request, user)
        return redirect("index")

    messages.info(request, "Invalid Credentials")
    return redirect("signin")


@login_required(login_url="signin")
def logout(request):
    auth_logout(request)
    return redirect("signin")
