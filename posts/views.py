from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, Group, User, Comment, Follow
from . forms import PostForm, CommentForm
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
            request,
            'index.html',
            {'page': page, 'paginator': paginator}
       )


def group_posts(request, slug):
    groups = get_object_or_404(Group, slug=slug)
    post_list = groups.group_posts.all()[:12]
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request, "group.html", {
        "group": groups, 
        "page": page, 
        "paginator": paginator
        })


@login_required()
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'new.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect("index")


def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts_list = user.author_posts.all()
    all_posts_count = user.author_posts.count()
    if request.user.is_authenticated:
        following = Follow.objects.filter(user=request.user, author=user).count()
    else:
        following = False
    paginator  = Paginator(posts_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'profile.html', {
            'profile': user, 
            'page': page, 
            'paginator': paginator, 
            'post_list': posts_list, 
            'all_posts_count': all_posts_count,
            'following': following
            })


def post_view(request, username, post_id):
    form = CommentForm()
    post = get_object_or_404(Post, pk=post_id, author__username=username) 
    all_posts_count = post.author.author_posts.count()
    comments = post.comments.all()
    return render(request, "post.html", {
            'post': post, 
            'profile': post.author, 
            'all_posts_count': all_posts_count,
            'comments': comments,
            'form': form,
            })


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect("post", username=request.user.username, post_id=post_id)
    return render(
        request, 'post_edit.html', {'form': form, 'post': post},
    )

@login_required
def add_comment(request, username, post_id):
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    all_posts_count = post.author.author_posts.count()
    comments = post.comments.all()
    if not form.is_valid():
        return render(request, "post.html", {
            'post': post,
            'profile': post.author,
            'all_posts_count': all_posts_count,
            'comments': comments,
            'form': form,
            })
    comment = form.save(commit=False)
    comment.author = request.user
    comment.post = post
    form.save()
    return redirect(reverse("post", kwargs={
        'username': username, 'post_id': post_id}))
    
    
def page_not_found(request, exception):
    return render(
        request, 
        "misc/404.html", 
        {"path": request.path}, 
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required  
def follow_index(request):
    favorite_authors = Follow.objects.select_related('author').filter(user=request.user).values_list("author")
    post_list = Post.objects.filter(author__in=favorite_authors)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request,
        "follow.html",
        {"page": page, "paginator": paginator}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.create(user=request.user, author=author)
    return redirect("profile", username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.get(user=request.user, author=author).delete()
    return redirect("profile", username=username)