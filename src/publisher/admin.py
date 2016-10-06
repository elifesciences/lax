from django.contrib import admin
import models

class ArticleVersionAdmin(admin.TabularInline):
    list_select_related = ('article',)
    readonly_fields = ('version', 'datetime_published', 'datetime_record_created', 'datetime_record_updated')
    fields = ('version', 'datetime_published', 'datetime_record_created')
    model = models.ArticleVersion
    extra = 0
    can_delete = False

    def has_add_permission(self, request):
        return False

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('manuscript_id', 'ejp_type', 'date_initial_qc', 'initial_decision', 'doi')
    list_filter = ('ejp_type', 'date_initial_qc', 'initial_decision', 'decision')  # ('is_published', admin.BooleanFieldListFilter))
    show_full_result_count = True
    search_fields = ('manuscript_id', 'doi',)
    inlines = [
        ArticleVersionAdmin,
    ]

admin_list = [
    (models.Publisher,),
    (models.Journal, ),
    (models.Article, ArticleAdmin),
]

[admin.site.register(*t) for t in admin_list]
