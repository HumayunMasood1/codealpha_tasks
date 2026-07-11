import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Profile, Post, Comment, Like, Follow


# ── Auto-create profile helper ──────────────────────────────────────────────
def get_or_create_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


# ── Feed ────────────────────────────────────────────────────────────────────
@login_required
def feed(request):
    get_or_create_profile(request.user)
    following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    posts = Post.objects.filter(
        Q(author__in=following_ids) | Q(author=request.user)
    ).select_related('author', 'author__profile').prefetch_related('likes', 'comments')

    liked_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)

    # Suggested users (not following, not self)
    suggested = User.objects.exclude(id=request.user.id).exclude(id__in=following_ids).order_by('?')[:5]
    for u in suggested:
        get_or_create_profile(u)

    return render(request, 'social/feed.html', {
        'posts': posts,
        'liked_ids': list(liked_ids),
        'suggested': suggested,
    })


def explore(request):
    posts = Post.objects.all().select_related('author', 'author__profile').prefetch_related('likes', 'comments')
    liked_ids = []
    if request.user.is_authenticated:
        liked_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    return render(request, 'social/explore.html', {'posts': posts, 'liked_ids': list(liked_ids)})


# ── Posts ────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def create_post(request):
    content = request.POST.get('content', '').strip()
    image_url = request.POST.get('image_url', '').strip()
    if content:
        Post.objects.create(author=request.user, content=content, image_url=image_url)
    return redirect('feed')


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    post.delete()
    return JsonResponse({'success': True})


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    get_or_create_profile(post.author)
    comments = post.comments.select_related('author', 'author__profile')
    liked = False
    if request.user.is_authenticated:
        liked = Like.objects.filter(user=request.user, post=post).exists()
    return render(request, 'social/post_detail.html', {
        'post': post, 'comments': comments, 'liked': liked
    })


# ── Comments ─────────────────────────────────────────────────────────────────
@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get('content', '').strip()
    if content:
        comment = Comment.objects.create(post=post, author=request.user, content=content)
        return JsonResponse({
            'success': True,
            'username': request.user.username,
            'content': comment.content,
            'time_ago': comment.time_ago(),
            'count': post.comments.count(),
        })
    return JsonResponse({'success': False})


# ── Likes ────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'liked': liked, 'count': post.likes_count()})


# ── Follow ───────────────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
        following = False
    else:
        following = True
    return JsonResponse({
        'following': following,
        'followers_count': Follow.objects.filter(following=target).count()
    })


# ── Profiles ─────────────────────────────────────────────────────────────────
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_or_create_profile(user)
    posts = Post.objects.filter(author=user).select_related('author').prefetch_related('likes', 'comments')
    is_following = False
    liked_ids = []
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()
        liked_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    followers = Follow.objects.filter(following=user).select_related('follower')
    following = Follow.objects.filter(follower=user).select_related('following')
    return render(request, 'social/profile.html', {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
        'is_following': is_following,
        'liked_ids': list(liked_ids),
        'followers': followers,
        'following': following,
    })


@login_required
def edit_profile(request):
    profile = get_or_create_profile(request.user)
    if request.method == 'POST':
        profile.bio = request.POST.get('bio', '')
        profile.avatar_url = request.POST.get('avatar_url', '')
        profile.website = request.POST.get('website', '')
        profile.location = request.POST.get('location', '')
        profile.save()
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        return redirect('profile', username=request.user.username)
    return render(request, 'social/edit_profile.html', {'profile': profile})


def search_view(request):
    q = request.GET.get('q', '').strip()
    users, posts = [], []
    if q:
        users = User.objects.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
        for u in users:
            get_or_create_profile(u)
        posts = Post.objects.filter(content__icontains=q).select_related('author', 'author__profile')
    return render(request, 'social/search.html', {'q': q, 'users': users, 'posts': posts})


# ── Auth ─────────────────────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 != password2:
            error = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already taken.'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters.'
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('feed')
    return render(request, 'social/register.html', {'error': error})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'feed'))
        error = 'Invalid username or password.'
    return render(request, 'social/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')
