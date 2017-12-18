from django.db.models import Count
from django.contrib import admin
from . import models, aws_events, fragment_logic

class ArticleVersionAdmin(admin.TabularInline):
    list_select_related = ('article',)
    readonly_fields = ('version', 'status', 'datetime_record_created', 'datetime_record_updated')
    fields = ('version', 'status', 'datetime_record_created', 'datetime_published')
    model = models.ArticleVersion
    extra = 0

    def has_add_permission(self, request):
        return False

class UnpublishedVersionsFilter(admin.SimpleListFilter):
    title = 'has unpublished'
    parameter_name = 'has-unpublished'

    def lookups(self, request, model_admin):
        return [
            ('unpublished', 'unpublished')
        ]

    def queryset(self, request, queryset):
        if self.value() != 'unpublished':
            return
        return queryset \
            .annotate(num_avs=Count('articleversion')) \
            .filter(num_avs__gt=0) \
            .filter(articleversion__datetime_published=None)

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('manuscript_id', 'volume', 'ejp_type', 'date_initial_qc', 'initial_decision', 'doi')
    list_filter = (UnpublishedVersionsFilter, 'volume', 'ejp_type', 'date_initial_qc', 'initial_decision', 'decision')  # ('is_published', admin.BooleanFieldListFilter))
    ordering = ('-manuscript_id',)
    show_full_result_count = True
    search_fields = ('manuscript_id', 'doi',)
    inlines = [
        ArticleVersionAdmin,
    ]

    # def save_model(self, request, art, form, change):
    #    super(ArticleAdmin, self).save_model(request, art, form, change)
    #    #aws_events.notify(art) # called in save_related, which is called after save_model()

    def delete_model(self, request, art):
        super(ArticleAdmin, self).delete_model(request, art)
        # simpler to disable hash check when updating many articles
        fragment_logic.set_all_article_json(art, quiet=True, hash_check=False)
        aws_events.notify(art.manuscript_id)

    def save_related(self, request, form, formsets, change):
        super(ArticleAdmin, self).save_related(request, form, formsets, change)
        art = form.instance
        # simpler to disable hash check when updating many articles
        fragment_logic.set_all_article_json(art, quiet=True, hash_check=False)
        aws_events.notify(art.manuscript_id)

admin_list = [
    (models.Publisher,),
    (models.Journal, ),
    (models.Article, ArticleAdmin),
]

[admin.site.register(*t) for t in admin_list]
