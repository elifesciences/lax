import re
from django.db import models
from autoslug import AutoSlugField
from simple_history.models import HistoricalRecords
from utils import second, firstnn

POA, VOR = 'poa', 'vor'

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

def ejp_type_choices():
    return [
        ('RA', 'Research article'),
        ('SR', 'Short report'),
        ('AV', 'Research advance'),
        ('RR', 'Registered report'),
        ('TR', 'Tools and resources')
    ]


AF = 'AF'
def decision_codes():
    return [
        ('RJI', 'Reject Initial Submission'),
        ('RJF', 'Reject Full Submission'),
        ('RVF', 'Revise Full Submission'),
        (AF, 'Accept Full Submission'),
        ('EF', 'Encourage Full Submission'),
        ('SW', 'Simple Withdraw')
    ]

class Article(models.Model):
    """The Article object represents what we know about an article right now.
    For things we don't know about an article but that are being sent to us,
    those go in to the ArticleAttribute key=val store. From there we can transition
    them into this table.

    THE ONLY REQUIRED FIELDS IN THIS MODEL ARE THE 'doi' and 'journal' FIELDS."""
    
    journal = models.ForeignKey(Journal)

    manuscript_id = models.PositiveIntegerField(unique=True, help_text="article identifier from beginning of submission process right through to end of publication.")

    # deprecated. the DOI is derived from the manuscript_id. this field will be going away.
    doi = models.CharField(max_length=255, unique=True, help_text="Article's unique ID in the wider world. All articles must have one as an absolute minimum")

    # this exists but isn't being considered. for reporting reasons, the 'submission date' is the date of the initial quality check
    datetime_submitted = models.DateTimeField(blank=True, null=True, help_text="Date author submitted article")

    # this field would be the most recent 'full decision accept' event
    #datetime_accepted = models.DateTimeField(blank=True, null=True, help_text="Date article accepted for publication")

    date_initial_qc = models.DateField(blank=True, null=True)
    date_initial_decision = models.DateField(blank=True, null=True)
    initial_decision = models.CharField(max_length=25, blank=True, null=True, choices=decision_codes())

    date_full_qc = models.DateField(blank=True, null=True)
    date_full_decision = models.DateField(blank=True, null=True)
    decision = models.CharField(max_length=25, blank=True, null=True, choices=decision_codes()) 

    date_rev1_qc = models.DateField(blank=True, null=True) 
    date_rev1_decision = models.DateField(blank=True, null=True) 
    rev1_decision = models.CharField(max_length=25, blank=True, null=True, choices=decision_codes()) 

    date_rev2_qc = models.DateField(blank=True, null=True) 
    date_rev2_decision = models.DateField(blank=True, null=True) 
    rev2_decision = models.CharField(max_length=25, blank=True, null=True, choices=decision_codes()) 

    date_rev3_qc = models.DateField(blank=True, null=True) 
    date_rev3_decision = models.DateField(blank=True, null=True) 
    rev3_decision = models.CharField(max_length=25, blank=True, null=True, choices=decision_codes()) 

    date_rev4_qc = models.DateField(blank=True, null=True) 
    date_rev4_decision = models.DateField(blank=True, null=True)
    rev4_decision = models.CharField(max_length=25, blank=True, null=True, choices=decision_codes()) 
    
    volume = models.PositiveSmallIntegerField(blank=True, null=True)
    website_path = models.CharField(max_length=50)

    # there is a real mess here with these article types
    # the actual preferred classification isn't being captured in any single place
    # full set of preferred naming can be captured from "display channel (Published)",
    # "NLM article type" then "sub display channel (published)"
    # https://docs.google.com/spreadsheets/d/1FpqQovdxt_VnR70SVVk7k3tjZnQnTAeURnc1PEtkz0k/edit#gid=0
    type = models.CharField(max_length=50, blank=True, null=True, help_text="xml article-type.") # research, editorial, etc
    ejp_type = models.CharField(max_length=3, choices=ejp_type_choices(), blank=True, null=True, \
                                    help_text="article as exported from EJP submission system") # RA, SR, etc

    datetime_record_created = models.DateTimeField(auto_now_add=True, help_text="Date this article was created")
    datetime_record_updated = models.DateTimeField(auto_now=True, help_text="Date this article was updated")

    history = HistoricalRecords()

    @property
    def date_accepted(self):
        # TODO: this sucks. normalize these into 'event' data or something
        x = [(self.initial_decision, self.date_initial_decision),
            (self.decision, self.date_full_decision),
            (self.rev1_decision, self.date_rev1_decision),
            (self.rev2_decision, self.date_rev2_decision),
            (self.rev3_decision, self.date_rev3_decision),
            (self.rev4_decision, self.date_rev4_decision)]
        return second(firstnn(filter(lambda p: p[0] == AF, x)))
    
    def earliest_poa(self):
        try:
            return self.articleversion_set.filter(status=POA).earliest('version')
        except models.ObjectDoesNotExist:
            return None

    def earliest_vor(self):
        try:
            return self.articleversion_set.filter(status=VOR).earliest('version')
        except models.ObjectDoesNotExist:
            return None

    @property
    def latest_version(self):
        return self.articleversion_set.latest('version')

    @property
    def earliest_version(self):
        return self.articleversion_set.earliest('version')        
    
    @property
    def datetime_published(self):
        return self.earliest_version.datetime_published

    @property
    def title(self):
        return self.latest_version.title

    @property
    def version(self):
        return self.latest_version.version

    class Meta:
        ordering = ('-date_initial_qc', )

    def dxdoi_url(self):
        return 'https://dx.doi.org/' + self.doi

    def get_absolute_url(self):
        return self.dxdoi_url()
    
    def __unicode__(self):
        return self.doi

    def __repr__(self):
        return u'<Article %s>' % self.doi

class ArticleVersion(models.Model):
    article = models.ForeignKey(Article) #, related_name='articleversion_set')

    title = models.CharField(max_length=255, null=True, blank=True, help_text='The title of the article')

    # positiveintegerfields allow zeroes
    version = models.PositiveSmallIntegerField(default=None, help_text="The version of the article. Version=None means pre-publication")
    status = models.CharField(max_length=3, choices=[(POA, 'POA'), (VOR, 'VOR')], blank=True, null=True)

    # NOTE: this value is currently wrong.
    # it's only ever correct for the first version of this article
    datetime_published = models.DateTimeField(blank=True, null=True, help_text="Date article first appeared on website")

    datetime_record_created = models.DateTimeField(auto_now_add=True, help_text="Date this article was created")
    datetime_record_updated = models.DateTimeField(auto_now=True, help_text="Date this article was updated")

    class Meta:
        unique_together = ('article', 'version')

    def get_absolute_url(self):
        return self.article.dxdoi_url()

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
