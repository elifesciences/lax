from django.contrib import admin
import models
from simple_history.admin import SimpleHistoryAdmin

class ArticleAdmin(SimpleHistoryAdmin):
    pass

class ArticleAttributeAdmin(SimpleHistoryAdmin):
    pass

admin_list = [
    (models.Publisher,),
    (models.Journal, ),
    (models.Article, ArticleAdmin),
    (models.ArticleAttribute, ArticleAttributeAdmin),
]

[admin.site.register(*t) for t in admin_list]
