from django.shortcuts import render
from annoying.decorators import render_to
import models

@render_to("publisher/landing.html")
def landing(request):
    return {}

@render_to("publisher/article-list.html")
def article_list(request):
    return {
        'article_list': models.Article.objects.all()
    }
