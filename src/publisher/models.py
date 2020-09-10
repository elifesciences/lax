from slugify import slugify
from django.db import models

# from .fields import JSONField
from functools import partial
from annoying.fields import JSONField
from .utils import msid2doi, mk_dxdoi_link, json_dumps, ordered_json_loads
from django.core.exceptions import ObjectDoesNotExist

JSONField = partial(JSONField, serializer=json_dumps, deserializer=ordered_json_loads)

POA, VOR = "poa", "vor"

# lsh@2020-09: todo, remove. should have been removed years ago
class Publisher(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Publisher %s>" % self.name


# lsh@2020-09: todo, remove. should have been removed years ago
class Journal(models.Model):
    publisher = models.ForeignKey(
        Publisher,
        null=True,
        on_delete=models.SET_NULL,
        help_text="A publisher may have many journals. A journal doesn't necessarily need a Publisher.",
    )
    name = models.CharField(
        max_length=255, unique=True, help_text="Name of the journal."
    )
    inception = models.DateTimeField(
        null=True, blank=True, help_text="Date journal was created."
    )

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Journal %s>" % self.name


# LSH@2017-05-31
# I've disabled the enforcement of the xml and ejp types in the model
# * we've had two instances where new ejp types caused lax to break or be hastily updated.
# * because adding new types requires a db migration
# * there is type wrangling in bot-lax
# * there is type wrangling in ejp-lax


def ejp_type_choices():
    return [
        ("RA", "Research article"),
        ("SR", "Short report"),
        ("AV", "Research advance"),
        ("RR", "Registered report"),
        ("TR", "Tools and resources"),
        ("RE", "Research exchange"),  # deprecated in favour of SC
        ("SC", "Scientific Correspondence"),
        ("RS", "Replication Study"),
        ("RC", "Research Communication"),
    ]


EJP_TYPE_IDX = dict(ejp_type_choices())
EJP_TYPE_REV_SLUG_IDX = {
    slugify(str(val), stopwords=["and"]): key for key, val in ejp_type_choices()
}


EDITORIAL, INSIGHT = "editorial", "insight"

# TODO: this mapping is unused and can be removed
def xml_type_choices():
    return [
        ("research-article", "Research article"),
        ("short-report", "Short report"),
        ("research-advance", "Research advance"),
        ("registered-report", "Registered report"),
        ("tools-resources", "Tools and resources"),
        ("replication-study", "Replication Study"),
        # not present in ejp
        ("correction", "Correction"),
        ("feature", "Feature article"),
        (INSIGHT, "Insight"),
        (EDITORIAL, "Editorial"),
        (None, "not set"),
    ]


AF = "AF"


def decision_codes():
    return [
        ("RJI", "Reject Initial Submission"),
        ("RJF", "Reject Full Submission"),
        ("RVF", "Revise Full Submission"),
        (AF, "Accept Full Submission"),
        ("EF", "Encourage Full Submission"),
        ("SW", "Simple Withdraw"),
    ]


class Article(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    manuscript_id = models.BigIntegerField(
        unique=True,
        help_text="article identifier from beginning of submission process right through to end of publication.",
    )
    # deprecated. the DOI is derived from the manuscript_id. this field will be going away.
    doi = models.CharField(
        max_length=255,
        unique=True,
        help_text="Article's unique ID in the wider world. All articles must have one as an absolute minimum",
    )

    # these come from the XML
    # insights, editorials and some feature articles don't have these values.
    date_received = models.DateField(
        blank=True,
        null=True,
        help_text="xml 'received' date. not all article types have this.",
    )
    date_accepted = models.DateField(
        blank=True,
        null=True,
        help_text="xml 'accepted' date. not all articles types have this. ",
    )

    @property
    def _doi(self):
        return msid2doi(self.manuscript_id)

    # these come from EJP

    # data exists but isn't being considered. for reporting reasons, 'submission date' is date of initial quality check
    # NOTE 2016-09-06: disabled. expectation of data in this field was becoming annoying.
    # datetime_submitted = models.DateTimeField(blank=True, null=True, help_text="Date author submitted article")

    # this field would be the most recent 'full decision accept' event
    # datetime_accepted = models.DateTimeField(blank=True, null=True, help_text="Date article accepted for publication")

    date_initial_qc = models.DateField(blank=True, null=True)
    date_initial_decision = models.DateField(blank=True, null=True)
    initial_decision = models.CharField(
        max_length=25, blank=True, null=True, choices=decision_codes()
    )

    date_full_qc = models.DateField(blank=True, null=True)
    date_full_decision = models.DateField(blank=True, null=True)
    decision = models.CharField(
        max_length=25, blank=True, null=True, choices=decision_codes()
    )

    date_rev1_qc = models.DateField(blank=True, null=True)
    date_rev1_decision = models.DateField(blank=True, null=True)
    rev1_decision = models.CharField(
        max_length=25, blank=True, null=True, choices=decision_codes()
    )

    date_rev2_qc = models.DateField(blank=True, null=True)
    date_rev2_decision = models.DateField(blank=True, null=True)
    rev2_decision = models.CharField(
        max_length=25, blank=True, null=True, choices=decision_codes()
    )

    date_rev3_qc = models.DateField(blank=True, null=True)
    date_rev3_decision = models.DateField(blank=True, null=True)
    rev3_decision = models.CharField(
        max_length=25, blank=True, null=True, choices=decision_codes()
    )

    date_rev4_qc = models.DateField(blank=True, null=True)
    date_rev4_decision = models.DateField(blank=True, null=True)
    rev4_decision = models.CharField(
        max_length=25, blank=True, null=True, choices=decision_codes()
    )

    volume = models.PositiveSmallIntegerField(blank=True, null=True)

    # there is a real mess here with these article types
    # the actual preferred classification isn't being captured in any single place
    # full set of preferred naming can be captured from "display channel (Published)",
    # "NLM article type" then "sub display channel (published)"
    # https://docs.google.com/spreadsheets/d/1FpqQovdxt_VnR70SVVk7k3tjZnQnTAeURnc1PEtkz0k/edit#gid=0
    type = models.CharField(
        max_length=50, blank=True, null=True, help_text="xml article-type."
    )  # research, editorial, etc
    ejp_type = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        help_text="article as exported from EJP submission system",
    )  # RA, SR, etc

    def ejp_rev_type(self):
        return EJP_TYPE_IDX.get(self.ejp_type, "unknown")

    datetime_record_created = models.DateTimeField(
        auto_now_add=True, help_text="Date this article was created"
    )
    datetime_record_updated = models.DateTimeField(
        auto_now=True, help_text="Date this article was updated"
    )

    def earliest_poa(self, defer=True):
        try:
            if defer:
                return (
                    self.articleversion_set.defer(
                        "article_json_v1", "article_json_v1_snippet"
                    )
                    .filter(status=POA)
                    .earliest("version")
                )
            return self.articleversion_set.filter(status=POA).earliest("version")
        except models.ObjectDoesNotExist:
            return None

    def earliest_vor(self, defer=True):
        try:
            if defer:
                return (
                    self.articleversion_set.defer(
                        "article_json_v1", "article_json_v1_snippet"
                    )
                    .filter(status=VOR)
                    .earliest("version")
                )
            return self.articleversion_set.filter(status=VOR).earliest("version")
        except models.ObjectDoesNotExist:
            return None

    @property
    def latest_version(self):
        return self.articleversion_set.latest("version")

    @property
    def earliest_version(self):
        return self.articleversion_set.earliest("version")

    @property
    def datetime_published(self):
        try:
            return self.earliest_version.datetime_published
        except ObjectDoesNotExist:
            return None

    @property
    def title(self):
        return self.latest_version.title

    @property
    def version(self):
        return self.latest_version.version

    class Meta:
        ordering = ("-date_initial_qc",)

    def dxdoi_url(self):
        return mk_dxdoi_link(self.doi)

    def get_absolute_url(self):
        return self.dxdoi_url()

    def __str__(self):
        return self.doi

    def __repr__(self):
        return "<Article %s>" % self.doi


class ArticleVersion(models.Model):
    # when the Article is deleted, delete this article version (never happens)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)

    title = models.CharField(
        max_length=255, null=True, blank=True, help_text="The title of the article"
    )

    # positiveintegerfields allow zeroes
    version = models.PositiveSmallIntegerField(
        default=None,
        help_text="The version of the article. Version=None means pre-publication",
    )
    status = models.CharField(
        max_length=3, choices=[(POA, "POA"), (VOR, "VOR")], blank=True, null=True
    )

    # NOTE: this value is currently wrong.
    # it's only ever correct for the first version of this article
    datetime_published = models.DateTimeField(
        blank=True, null=True, help_text="Date article first appeared on website"
    )

    # TODO: rename these fields to 'article_json' and 'article_json_snippet'
    article_json_v1 = JSONField(null=True, blank=True, help_text="Valid article-json.")
    article_json_v1_snippet = JSONField(
        null=True,
        blank=True,
        help_text="Valid article-json snippet, extracted from the valid article-json",
    )
    # TODO: remove NULL constraint once everything has a hash.
    article_json_hash = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="md5 digest of merged result. see `fragment_logic.hash_ajson` for algorithm",
    )

    datetime_record_created = models.DateTimeField(
        auto_now_add=True, help_text="Date this article was created"
    )
    datetime_record_updated = models.DateTimeField(
        auto_now=True, help_text="Date this article was updated"
    )

    class Meta:
        ordering = ("version",)  # ASC, earliest to latest
        unique_together = ("article", "version")

    def published(self):
        "returns True if this version of the article has a publication date"
        return self.datetime_published is not None

    def get_absolute_url(self):
        return self.article.dxdoi_url()

    def __str__(self):
        return "%s v%s" % (self.article.manuscript_id, self.version)

    def __repr__(self):
        return "<ArticleVersion %s>" % self


# the bulk of the article data, derived from the xml via the bot-lax adaptor
XML2JSON = "xml->json"


class ArticleFragment(models.Model):
    # when the Article is deleted, delete this article fragment
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        help_text="all fragments belong to an article, only some fragments belong to an article version",
    )
    version = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="if null, fragment applies only to a specific version of article",
    )
    type = models.CharField(
        max_length=25, help_text='the type of fragment, eg "xml", "content-header", etc'
    )
    fragment = JSONField(help_text="partial piece of article data to be merged in")
    position = models.PositiveSmallIntegerField(
        default=1,
        help_text="position in the merge order with lower fragments merged first",
    )

    datetime_record_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.version:
            return '%s v%s "%s"' % (self.article.manuscript_id, self.version, self.type)
        return '%s "%s"' % (self.article.manuscript_id, self.type)

    def __repr__(self):
        return "<ArticleFragment %s>" % self

    class Meta:
        # an article can only have one instance of a fragment type
        unique_together = ("article", "type", "version")
        # multiple fragments at position=1 will be ordered by the date they were added
        # lowest positions first (ASC), earliest creation date first (ASC)
        ordering = ("position", "datetime_record_created")


DATE_EJP_QC, DATE_EJP_DECISION = "date-qc", "date-decision"
DATE_XML_RECEIVED, DATE_XML_ACCEPTED = "date-xml-received", "date-xml-accepted"
DATETIME_ACTION_INGEST, DATETIME_ACTION_PUBLISH = (
    "datetime-action-ingest",
    "datetime-action-publish",
)


def article_event_choices():
    return [
        (DATE_EJP_QC, "quality check date"),
        (DATE_EJP_DECISION, "decision date"),
        (DATE_XML_RECEIVED, "received date (XML)"),
        (DATE_XML_ACCEPTED, "accepted date (XML)"),
        (DATETIME_ACTION_INGEST, "'ingest' event"),
        (DATETIME_ACTION_PUBLISH, "'publish' event"),
        # ('date-ejp-received', 'date received (EJP)'),
    ]


class ArticleEvent(models.Model):
    # when the Article is deleted, delete this article event
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    event = models.CharField(max_length=25, choices=article_event_choices())
    datetime_event = models.DateTimeField()
    value = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="a value, if any, associated with this event",
    )

    class Meta:
        # this means if the times on certain events change, they'll get a new event
        unique_together = ("article", "event", "datetime_event")
        ordering = (
            "datetime_event",
            "event",
        )  # least to most recent (ASC), then alphabetically by event type

    def __str__(self):
        return "%s: %s" % (self.event, self.value or self.datetime_event)

    def __repr__(self):
        return "<ArticleEvent %s>" % self.event


class ArticleVersionRelation(models.Model):
    # when the ArticleVersion is deleted, delete this internal relationship
    articleversion = models.ForeignKey(ArticleVersion, on_delete=models.CASCADE)
    # when the related Article is deleted, delete this internal relationship
    related_to = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        help_text="the Article this ArticleVersion is related to",
    )

    class Meta:
        unique_together = ("articleversion", "related_to")

    def __str__(self):
        return "%s => %s" % (self.articleversion, self.related_to.manuscript_id)

    def __repr__(self):
        return "<ArticleVersionRelation %s>" % self


class ArticleVersionExtRelation(models.Model):
    # when the ArticleVersion is deleted, delete this external relationship
    articleversion = models.ForeignKey(ArticleVersion, on_delete=models.CASCADE)
    uri = models.URLField(max_length=2000, help_text="location of external object")
    citation = JSONField(help_text="snippet of json describing the external link")

    class Meta:
        unique_together = ("articleversion", "uri")

    def __str__(self):
        return "%s => %s" % (self.articleversion, self.uri)

    def __repr__(self):
        return "<ArticleVersionRelation %s>" % self
