import re
from django.db import models
from autoslug import AutoSlugField
from simple_history.models import HistoricalRecords

class Publisher(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return u'<Publisher %s>' % self.name

class Journal(models.Model):
    publisher = models.ForeignKey(Publisher, null=True, help_text="A publisher may have many journals. A journal doesn't necessarily need a Publisher.")
    name = models.CharField(max_length=255, help_text="Name of the journal.")
    inception = models.DateTimeField(null=True, blank=True, help_text="Date journal was created.")

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return u'<Journal %s>' % self.name

class Article(models.Model):
    """The Article object represents what we know about an article right now.
    For things we don't know about an article but that are being sent to us,
    those go in to the ArticleAttribute key=val store. From there we can transition
    them into this table.

    THE ONLY REQUIRED FIELDS IN THIS MODEL ARE THE 'doi' and 'journal' FIELDS."""
    
    journal = models.ForeignKey(Journal)

    doi = models.CharField(max_length=255, unique=True, help_text="Article's unique ID in the wider world. All articles must have one as an absolute minimum")
    
    title = models.CharField(max_length=255, null=True, blank=True, help_text='The title of the article')
    slug = AutoSlugField(null=True, blank=True, populate_from='title', always_update=True, help_text='A friendlier version of the title for machines')

    # possible custom managers ?
    # research_articles
    # non_research_articles
    # recently_published

    volume = models.PositiveSmallIntegerField(blank=True, null=True)
    website_path = models.CharField(max_length=50)

    type = models.CharField(max_length=50, blank=True, null=True) # research, editorial, etc
    
    datetime_submitted = models.DateTimeField(blank=True, null=True, help_text="Date author submitted article")
    datetime_accepted = models.DateTimeField(blank=True, null=True, help_text="Date article accepted for publication")

    datetime_record_created = models.DateTimeField(auto_now_add=True, help_text="Date this article was created")
    datetime_record_updated = models.DateTimeField(auto_now=True, help_text="Date this article was updated")

    history = HistoricalRecords()

    @property
    def version(self):
        return self.articleversion_set.latest('version').version
    
    def dxdoi_url(self):
        return 'https://dx.doi.org/' + self.doi

    def get_absolute_url(self):
        return self.dxdoi_url()
    
    def __unicode__(self):
        return self.title

    def __repr__(self):
        return u'<Article %s>' % self.doi

class ArticleVersion(models.Model):
    article = models.ForeignKey(Article)
    # positiveintegerfields allow zeroes
    version = models.PositiveSmallIntegerField(default=None, help_text="The version of the article. Version=None means pre-publication")
    status = models.CharField(max_length=3, choices=[('poa', 'POA'), ('vor', 'VOR')], blank=True, null=True)

    datetime_published = models.DateTimeField(blank=True, null=True, help_text="Date article first appeared on website")

    datetime_record_created = models.DateTimeField(auto_now_add=True, help_text="Date this article was created")
    datetime_record_updated = models.DateTimeField(auto_now=True, help_text="Date this article was updated")

    class Meta:
        unique_together = ('article', 'version')
    
    def __unicode__(self):
        return '%s v%s' % (self.article.doi, self.version)
    
    def __repr__(self):
        return u'<Article %s>' % self


#
# as of 2016.04.06, ArticleAttributes are not being used.
# they were introduced for not-great reasons.
# I would suggest tearing them out.
#
    
    
def attr_type_choices():
    return [
        ('char', 'String'), # first element is the default

        ('int', 'Integer'),
        ('float', 'Float'),
        ('date', 'Date'),

        # this also allows us to put in custom types ...
        #('td', 'TimeDelta'),
        #('ref', 'ACME Identifing Service'),
    ]

DEFAULT_ATTR_TYPE = attr_type_choices()[0][0]
SUPERSLUG = re.compile('[\d\-]+')

class AttributeType(models.Model):
    name = models.SlugField(max_length=50)
    type = models.CharField(max_length=10, choices=attr_type_choices(), default=DEFAULT_ATTR_TYPE)
    description = models.TextField(blank=True, null=True)

    def save(self):
        self.name = re.sub(SUPERSLUG, '', self.name).lower()
        super(AttributeType, self).save()

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return u'<AttributeType %s (%s)>' % (self.name, self.type)

class ArticleAttribute(models.Model):
    article = models.ForeignKey(Article)
    key = models.ForeignKey(AttributeType)
    value = models.CharField(max_length=255)
    
    datetime_record_created = models.DateTimeField(auto_now_add=True, help_text="Date this attribute was created")
    datetime_record_updated = models.DateTimeField(auto_now=True, help_text="Date this attribute was updated")

    history = HistoricalRecords()

    class Meta:
        # there can be many 'Foo' attributes but only one combination of Article+'Foo'
        # for example there can only be one SomeArticleV1.SubmissionDate.
        # SomeArticleV1 cannot have multiple SubmissionDate.
        # This cardinality might be tied to AttributeType if necessary
        unique_together = ('article', 'key')

    def __unicode__(self):
        return '%s=%s' % (self.key.name, self.value)

    def __repr__(self):
        return u'<ArticleAttribute %s>' % self.__unicode__()

class ArticleCorrection(models.Model):
    article = models.ForeignKey(Article)
    description = models.TextField(blank=True, null=True, help_text="free text to describe what the correction was. optional.")
    datetime_corrected = models.DateTimeField(help_text="Date and time a correction was made to this article.")

    def __unicode__(self):
        return '%s (corrected %s)' % (self.article, self.datetime_article_corrected.strftime("%Y-%m-%d"))

    def __repr__(self):
        return u'<ArticleCorrection %s>' % self.article
