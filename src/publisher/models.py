from django.db import models

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
    journal = models.ForeignKey(Journal)
    title = models.CharField(max_length=255)
    # a doi+version constitute a unique article
    doi = models.CharField(max_length=255, null=True, blank=True, unique=True)
    version = models.PositiveSmallIntegerField(default=1)

    # possible custom managers ?
    # research_articles
    # non_research_articles
    # recently_published

    # events shifted into separate key-val table
    # TODO: look at the events we are now capturing and see
    # if (for the sake of convenience) can be modelled here
    # like the below
    
    #date_added = models.DateTimeField(auto_now_add=True)
    #date_submitted = models.DateTimeField(blank=True, null=True)    
    #date_published = models.DateTimeField(blank=True, null=True)
    #date_accepted = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [
            ("doi", "version")
        ]

    def __unicode__(self):
        return self.title

    def __repr__(self):
        return u'<Article %s>' % self.title

def attr_type_choices():
    return [
        ('char', 'String'),
        ('int', 'Integer'),
        ('float', 'Float'),
        ('date', 'Date'),

        # this also allows us to put in custom types ...
        #('td', 'TimeDelta'),
        #('ref', 'ACME Identifing Service'),
    ]

class AttributeType(models.Model):
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=attr_type_choices())
    description = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return u'<AttributeType %s (%s)>' % (self.name, self.type)

class ArticleAttribute(models.Model):
    key = models.ForeignKey(AttributeType)
    value = models.CharField(max_length=255)

    def __unicode__(self):
        return '%s=%s' % (self.key.name, self.value)

    def __repr__(self):
        return u'<ArticleAttribute %s>' % self.__unicode__()
