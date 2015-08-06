from django.contrib import admin
import models
from simple_history.admin import SimpleHistoryAdmin

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('doi', 'title', 'datetime_published')
    list_filter = ('datetime_published', 'status', 'volume', 'type')

class ArticleAttributeAdmin(admin.ModelAdmin):
    pass

admin_list = [
    (models.Publisher,),
    (models.Journal, ),
    (models.Article, ArticleAdmin),
    (models.ArticleAttribute, ArticleAttributeAdmin),
]

[admin.site.register(*t) for t in admin_list]
