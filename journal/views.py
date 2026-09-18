from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Post, Tag


def health(request):
    return HttpResponse("ok")


def home(request):
    posts = Post.objects.filter(published=True).prefetch_related("tags")
    featured = posts.filter(featured=True).first() or posts.first()
    rest = posts.exclude(pk=featured.pk) if featured else posts
    return render(
        request,
        "journal/home.html",
        {"featured": featured, "posts": rest},
    )


def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.prefetch_related("tags"), slug=slug, published=True
    )
    others = (
        Post.objects.filter(published=True).exclude(pk=post.pk)[:3]
    )
    return render(request, "journal/post.html", {"post": post, "others": others})


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    posts = Post.objects.filter(published=True, tags=tag).prefetch_related("tags")
    return render(request, "journal/tag.html", {"tag": tag, "posts": posts})
