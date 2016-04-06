from django.contrib import admin
import models
from simple_history.admin import SimpleHistoryAdmin

class ArticleVersionAdmin(admin.TabularInline):
    model = models.ArticleVersion
    extra = 0

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('doi', 'title')
    list_filter = ('volume', 'type')
    search_fields = ('doi', 'title')
    inlines = [
        ArticleVersionAdmin,
    ]


class ArticleAttributeAdmin(admin.ModelAdmin):
    pass

admin_list = [
    (models.Publisher,),
    (models.Journal, ),
    (models.Article, ArticleAdmin),
    (models.ArticleAttribute, ArticleAttributeAdmin),
]

[admin.site.register(*t) for t in admin_list]
