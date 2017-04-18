from django.contrib import admin
from . import models, aws_events

class ArticleVersionAdmin(admin.TabularInline):
    list_select_related = ('article',)
    readonly_fields = ('version', 'status', 'datetime_record_created', 'datetime_record_updated')
    fields = ('version', 'status', 'datetime_record_created', 'datetime_published')
    model = models.ArticleVersion
    extra = 0

    def has_add_permission(self, request):
        return False

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('manuscript_id', 'volume', 'ejp_type', 'date_initial_qc', 'initial_decision', 'doi')
    list_filter = ('volume', 'ejp_type', 'date_initial_qc', 'initial_decision', 'decision')  # ('is_published', admin.BooleanFieldListFilter))
    ordering = ('-manuscript_id',)
    show_full_result_count = True
    search_fields = ('manuscript_id', 'doi',)
    inlines = [
        ArticleVersionAdmin,
    ]

    def save_model(self, request, art, form, change):
        super(ArticleAdmin, self).save_model(request, art, form, change)
        aws_events.notify(art)

    def delete_model(self, request, art):
        super(ArticleAdmin, self).delete_model(request, art)
        aws_events.notify(art)

    # this may cause multiple events to be sent
    def save_related(self, request, form, formsets, change):
        super(ArticleAdmin, self).save_related(request, form, formsets, change)
        art = form.instance
        aws_events.notify(art)

admin_list = [
    (models.Publisher,),
    (models.Journal, ),
    (models.Article, ArticleAdmin),
]

[admin.site.register(*t) for t in admin_list]
