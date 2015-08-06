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
    slug = AutoSlugField(null=True, blank=True, populate_from='title', help_text='A friendlier version of the title for machines')

    version = models.PositiveSmallIntegerField(default=1, help_text="The version of the article. All articles have at least a version 1")

    # possible custom managers ?
    # research_articles
    # non_research_articles
    # recently_published

    volume = models.PositiveSmallIntegerField(blank=True, null=True)
    status = models.CharField(max_length=3, choices=[('poa', 'POA'), ('vor', 'VOR')], blank=True, null=True)
    website_path = models.CharField(max_length=50)

    type = models.CharField(max_length=50, blank=True, null=True)
    
    datetime_submitted = models.DateTimeField(blank=True, null=True, help_text="Date author submitted article")
    datetime_accepted = models.DateTimeField(blank=True, null=True, help_text="Date article accepted for publication")
    datetime_published = models.DateTimeField(blank=True, null=True, help_text="Date article first appeared on website")
    
    datetime_record_created = models.DateTimeField(auto_now_add=True, help_text="Date this article was created")
    datetime_record_updated = models.DateTimeField(auto_now=True, help_text="Date this article was updated")

    history = HistoricalRecords()
    
    def __unicode__(self):
        return self.title

    def __repr__(self):
        return u'<Article %s v%s>' % (self.doi, self.version)

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

class AttributeType(models.Model):
    name = models.CharField(max_length=50)
    slug = AutoSlugField(populate_from='name')
    type = models.CharField(max_length=10, choices=attr_type_choices())
    description = models.TextField(blank=True, null=True)

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

    def __unicode__(self):
        return '%s=%s' % (self.key.name, self.value)

    def __repr__(self):
        return u'<ArticleAttribute %s>' % self.__unicode__()
